"""
notebooklm_weekly.py — Track B orchestrator
Runs weekly (Sunday, deadline 23h30) via notebooklm-weekly.sh.

Architecture:
  NLMClient        — MCP stdio JSON-RPC wrapper (subprocess)
  NotebookManager  — nlm-notebooks.json CRUD + rotation
  GroundingRouter  — NLM query response → verdict enum + confidence
  CircuitBreaker   — nlm-status.json state machine

Usage:
    python3 notebooklm_weekly.py [--domain ai|iot|cloud|ecommerce] [--dry-run]

Env:
    NLM_MCP_CMD  — MCP server command (default: notebooklm-mcp)
    VAULT_ROOT   — Vault root (default: ~/Documents/Obsidian/KnowledgeBase)
"""
import argparse
import json
import os
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import yaml

# ── Paths ─────────────────────────────────────────────────────────────────────
VAULT = Path(os.environ.get("VAULT_ROOT", Path.home() / "Documents/Obsidian/KnowledgeBase"))
META_DIR = VAULT / "_meta"
LOGS_DIR = VAULT / "_logs"
CONCEPTS_DIR = VAULT / "_inbox/raw/concepts"
PAPERS_DIR = VAULT / "_inbox/raw/papers"

DOMAINS = ["ai", "iot", "cloud", "ecommerce"]
ROTATION_THRESHOLD = 45


# ── Exceptions ────────────────────────────────────────────────────────────────
class NLMClientError(Exception):
    pass


# ── Frontmatter helpers ───────────────────────────────────────────────────────
def parse_frontmatter(text: str) -> Optional[dict]:
    """Extract YAML frontmatter from markdown text. Returns None if absent."""
    if not text.startswith("---"):
        return None
    end = text.find("---", 3)
    if end == -1:
        return None
    try:
        return yaml.safe_load(text[3:end]) or {}
    except yaml.YAMLError:
        return None


def extract_h1_title(text: str) -> str:
    """Return first H1 line (without '# '), or empty string."""
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def sanitize_paper_id(paper_id: str) -> str:
    """Replace ':' and '.' with '-' for safe filename use."""
    return paper_id.replace(":", "-").replace(".", "-")


# ── NLMClient ─────────────────────────────────────────────────────────────────
class NLMClient:
    """
    Minimal MCP stdio client for notebooklm-mcp.

    Starts the MCP server as a subprocess, sends JSON-RPC 2.0 messages
    over stdin, and reads responses from stdout.
    """

    def __init__(self, cmd: Optional[str] = None, timeout: int = 90):
        self.cmd = cmd or os.environ.get("NLM_MCP_CMD", "notebooklm-mcp")
        self.timeout = timeout
        self._proc: Optional[subprocess.Popen] = None
        self._next_id = 1
        self._id_lock = threading.Lock()
        self._response_q: queue.Queue = queue.Queue()
        self._reader_thread: Optional[threading.Thread] = None
        self._stderr_thread: Optional[threading.Thread] = None
        self._stderr_lines: list = []
        self._subprocess_dead = False

    def __enter__(self) -> "NLMClient":
        self._start()
        return self

    def __exit__(self, *_) -> None:
        self._stop()

    def _start(self) -> None:
        try:
            self._proc = subprocess.Popen(
                [self.cmd],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
        except FileNotFoundError:
            raise NLMClientError(
                f"MCP command '{self.cmd}' not found. "
                "Install your fork: npm install -g git+https://github.com/<you>/notebooklm-mcp#<sha>"
            )
        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reader_thread.start()
        # Drain stderr continuously — prevents PIPE-buffer deadlock on verbose stderr
        self._stderr_thread = threading.Thread(target=self._stderr_loop, daemon=True)
        self._stderr_thread.start()
        self._initialize()

    def _stop(self) -> None:
        if self._proc:
            try:
                self._proc.stdin.close()
                self._proc.wait(timeout=5)
            except Exception:
                self._proc.kill()

    def _read_loop(self) -> None:
        for line in self._proc.stdout:
            line = line.strip()
            if line:
                try:
                    self._response_q.put(json.loads(line))
                except json.JSONDecodeError:
                    pass
        # stdout closed → subprocess exited. Push sentinel so _send wakes up.
        self._subprocess_dead = True
        self._response_q.put({"__dead__": True})

    def _stderr_loop(self) -> None:
        """Drain stderr into a buffer (cap 200 lines) to prevent PIPE deadlock."""
        for line in self._proc.stderr:
            if len(self._stderr_lines) < 200:
                self._stderr_lines.append(line.rstrip())

    def _stderr_tail(self, n: int = 10) -> str:
        return "\n".join(self._stderr_lines[-n:])

    def _send(self, method: str, params: Optional[dict] = None, *, notify: bool = False) -> Optional[dict]:
        if self._subprocess_dead:
            raise NLMClientError(
                f"MCP subprocess exited (code={self._proc.poll()}). "
                f"stderr tail:\n{self._stderr_tail()}"
            )
        msg: dict = {"jsonrpc": "2.0", "method": method}
        msg_id = None
        if not notify:
            with self._id_lock:
                msg_id = self._next_id
                self._next_id += 1
            msg["id"] = msg_id
        if params is not None:
            msg["params"] = params
        try:
            self._proc.stdin.write(json.dumps(msg) + "\n")
            self._proc.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise NLMClientError(
                f"MCP subprocess stdin closed during '{method}' "
                f"(exit={self._proc.poll()}). stderr tail:\n{self._stderr_tail()}"
            ) from exc
        if notify:
            return None
        deadline = time.time() + self.timeout
        pending: list = []
        while time.time() < deadline:
            try:
                resp = self._response_q.get(timeout=1.0)
                # Sentinel from reader thread: subprocess died mid-request
                if resp.get("__dead__"):
                    raise NLMClientError(
                        f"MCP subprocess exited during '{method}' "
                        f"(code={self._proc.poll()}). stderr tail:\n{self._stderr_tail()}"
                    )
                if resp.get("id") == msg_id:
                    for m in pending:
                        self._response_q.put(m)
                    if "error" in resp:
                        raise NLMClientError(
                            f"MCP error {resp['error']['code']}: {resp['error']['message']}"
                        )
                    return resp.get("result")
                pending.append(resp)
            except queue.Empty:
                pass
        for m in pending:
            self._response_q.put(m)
        raise NLMClientError(f"Timeout ({self.timeout}s) waiting for response to '{method}'")

    def _initialize(self) -> None:
        self._send("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "nlm-weekly", "version": "2.0.0"},
        })
        self._send("notifications/initialized", notify=True)

    def call_tool(self, name: str, arguments: dict) -> str:
        """Call an MCP tool and return the first text content block."""
        result = self._send("tools/call", {"name": name, "arguments": arguments})
        content = (result or {}).get("content", [])
        if not content:
            raise NLMClientError(f"Tool '{name}' returned empty content")
        return content[0].get("text", "")


# ── NotebookManager ───────────────────────────────────────────────────────────
class NotebookManager:
    """
    Manages _meta/nlm-notebooks.json.

    Schema (per domain):
      current: { id, source_count, created, pushed_paper_ids }
      previous: same | null
    """

    def __init__(self, path: Path):
        self.path = path

    def load(self) -> dict:
        if not self.path.exists():
            raise FileNotFoundError(
                f"{self.path} not found. Run Task 1 bootstrap to create it."
            )
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, data: dict) -> None:
        """Atomic write via temp-file + rename (POSIX atomic)."""
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)

    def needs_rotation(self, domain_data: dict) -> bool:
        current = domain_data.get("current")
        return (
            current is not None
            and current.get("source_count", 0) >= ROTATION_THRESHOLD
        )

    def rotate(self, domain_data: dict, new_notebook_id: str) -> dict:
        """Move current → previous, create fresh current."""
        new_data = dict(domain_data)
        new_data["previous"] = domain_data.get("current")
        new_data["current"] = {
            "id": new_notebook_id,
            "source_count": 0,
            "created": date.today().isoformat(),
            "pushed_paper_ids": [],
        }
        return new_data

    def increment_source_count(self, domain_data: dict, paper_id: str) -> dict:
        new_data = dict(domain_data)
        current = dict(new_data["current"])
        current["source_count"] = current.get("source_count", 0) + 1
        pushed = list(current.get("pushed_paper_ids", []))
        pushed.append(paper_id)
        current["pushed_paper_ids"] = pushed
        new_data["current"] = current
        return new_data

    def get_new_papers(self, domain_data: dict, all_paper_ids: list) -> list:
        """Return paper_ids not yet pushed to current or previous notebook."""
        pushed: set = set()
        for nb_key in ("current", "previous"):
            nb = domain_data.get(nb_key)
            if nb:
                pushed.update(nb.get("pushed_paper_ids", []))
        return [pid for pid in all_paper_ids if pid not in pushed]


# ── GroundingRouter ───────────────────────────────────────────────────────────
_SUPPORT_PHRASES = [
    "support", "confirm", "demonstrate", "show", "evidence",
    "consistent with", "aligned with", "according to", "validates",
    "corroborates",
]
_DISPUTE_PHRASES = [
    "contradict", "dispute", "conflict", "inconsistent", "contrary",
    "however, the source", "mixed evidence", "challenges this",
    "contradicted by",
]


def _count_sources(text: str) -> int:
    return len(re.findall(r"\[Source \d+\]|\[Ref \d+\]|\(\d{4}\)", text))


class GroundingRouter:
    """Maps NLM notebook_query response text → (verdict, confidence)."""

    @staticmethod
    def parse_verdict(response_text: str) -> tuple:
        """
        Returns (verdict, confidence) where verdict is one of:
          supported | partially_supported | disputed | insufficient_evidence
        """
        if not response_text or not response_text.strip():
            return "insufficient_evidence", 0.0

        text_lower = response_text.lower()
        source_count = _count_sources(response_text)
        dispute_hits = sum(1 for p in _DISPUTE_PHRASES if p in text_lower)
        support_hits = sum(1 for p in _SUPPORT_PHRASES if p in text_lower)

        if source_count < 2 and support_hits < 2:
            return "insufficient_evidence", 0.0
        if dispute_hits > 0 and dispute_hits >= support_hits:
            confidence = round(max(0.10, 0.50 - dispute_hits * 0.10), 2)
            return "disputed", confidence
        if support_hits >= 2:
            confidence = round(min(0.95, 0.65 + source_count * 0.05 + support_hits * 0.03), 2)
            return "supported", confidence
        if support_hits == 1:
            return "partially_supported", 0.60
        return "insufficient_evidence", 0.0


# ── CircuitBreaker ────────────────────────────────────────────────────────────
class CircuitBreaker:
    """
    Manages _logs/nlm-status.json.

    States:
      not_initialized — never run
      complete        — last run succeeded
      failed          — last run failed, consecutive_failures incremented
    """

    def __init__(self, path: Path):
        self.path = path

    def load(self) -> dict:
        if not self.path.exists():
            return {"status": "not_initialized", "consecutive_failures": 0, "complete": False}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def record_success(self, stats: dict) -> None:
        payload = {
            "status": "complete",
            "complete": True,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "consecutive_failures": 0,
            **stats,
        }
        self._write(payload)

    def record_failure(self, reason: str) -> int:
        current = self.load()
        failures = current.get("consecutive_failures", 0) + 1
        payload = {
            "status": "failed",
            "complete": False,
            "reason": reason,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "consecutive_failures": failures,
        }
        self._write(payload)
        return failures

    def _write(self, payload: dict) -> None:
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)


# ── File I/O helpers ──────────────────────────────────────────────────────────
def write_grounded_note(
    paper_id: str,
    tier: str,
    source_chain: list,
    verdict: str,
    confidence: float,
    notebook_ids: list,
    nlm_response: str,
    output_dir: Path,
    today: str,
) -> Path:
    """
    Write B-{paper_id_sanitized}-grounded.md to output_dir.
    Adds <!-- review-flag: nlm-disputed --> when verdict == 'disputed'.
    """
    pid_sanitized = sanitize_paper_id(paper_id)
    path = output_dir / f"B-{pid_sanitized}-grounded.md"

    frontmatter = {
        "type": "concept",
        "maturity": "fleeting",
        "tier": tier,
        "created": today,
        "paper_id": paper_id,
        "source_chain": source_chain,
        "nlm_grounding": {
            "verdict": verdict,
            "confidence": confidence,
            "notebook_ids": notebook_ids,
        },
    }
    review_flag = "\n<!-- review-flag: nlm-disputed -->\n" if verdict == "disputed" else ""
    content = (
        f"---\n"
        f"{yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False)}"
        f"---\n"
        f"{review_flag}\n"
        f"{nlm_response}\n"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def load_tier_s_concepts(concepts_dir: Path) -> list:
    """
    Load all A-*.md files with tier: S from frontmatter.
    Returns list of dicts: {path, paper_id, tier, source_chain, title}
    """
    concepts = []
    for f in sorted(concepts_dir.glob("A-*.md")):
        text = f.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        if not fm or fm.get("tier") != "S":
            continue
        concepts.append({
            "path": f,
            "paper_id": fm.get("paper_id", ""),
            "tier": "S",
            "source_chain": fm.get("source_chain", []),
            "title": extract_h1_title(text),
        })
    return concepts


def load_new_papers(domain: str, domain_data: dict, papers_dir: Optional[Path] = None) -> list:
    """
    Load papers from _inbox/raw/papers/{domain}/ not yet pushed to any NLM notebook.
    Returns list of dicts: {paper_id, title, abstract, source_chain, path}
    """
    base = papers_dir or (PAPERS_DIR / domain)
    if not base.exists():
        return []

    pushed: set = set()
    for nb_key in ("current", "previous"):
        nb = domain_data.get(nb_key)
        if nb:
            pushed.update(nb.get("pushed_paper_ids", []))

    papers = []
    for f in sorted(base.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        if not fm:
            continue
        paper_id = fm.get("paper_id", "")
        if not paper_id or paper_id in pushed:
            continue
        papers.append({
            "paper_id": paper_id,
            "title": fm.get("title", ""),
            "abstract": fm.get("abstract", ""),
            "source_chain": [
                f"origin: {fm.get('url', '')}",
                "via: abstract",
            ],
            "path": f,
        })
    return papers


def _infer_domain(paper_id: str) -> Optional[str]:
    """Find which domain this paper belongs to by scanning papers directories."""
    for domain in DOMAINS:
        for papers_subdir in [PAPERS_DIR / domain, PAPERS_DIR / domain / "_processed"]:
            if not papers_subdir.exists():
                continue
            for f in papers_subdir.glob("*.md"):
                text = f.read_text(encoding="utf-8")
                fm = parse_frontmatter(text)
                if fm and fm.get("paper_id") == paper_id:
                    return domain
    return None


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(
        description="NotebookLM Track B — weekly paper ingestion and concept grounding"
    )
    parser.add_argument("--domain", choices=DOMAINS, default=None,
                        help="Single domain (default: all)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print actions without calling NLM MCP")
    args = parser.parse_args()

    cb = CircuitBreaker(LOGS_DIR / "nlm-status.json")
    nb_mgr = NotebookManager(META_DIR / "nlm-notebooks.json")
    today = date.today().isoformat()
    domains_to_run = [args.domain] if args.domain else DOMAINS
    stats: dict = {
        "domains_processed": [],
        "papers_added": 0,
        "concepts_grounded": 0,
        "rotations": [],
    }

    notebook_data = None
    try:
        notebook_data = nb_mgr.load()

        if args.dry_run:
            for domain in domains_to_run:
                domain_data = notebook_data["domains"].get(
                    domain, {"current": None, "previous": None}
                )
                new_papers = load_new_papers(domain, domain_data)
                print(f"\n── Domain: {domain} ─────────────────")
                print(f"  Current notebook: {(domain_data.get('current') or {}).get('id', 'NONE')}")
                if nb_mgr.needs_rotation(domain_data):
                    print("  [dry-run] Would rotate notebook (source_count >= 45)")
                print(f"  [dry-run] Would add {len(new_papers)} paper(s) to NLM")
                for p in new_papers:
                    print(f"    {p['paper_id']}: {p['title'][:60]}")
            tier_s = load_tier_s_concepts(CONCEPTS_DIR)
            print(f"\n  [dry-run] Would ground {len(tier_s)} Tier S concept(s)")
            for c in tier_s:
                print(f"    {c['paper_id']}: {c['title'][:60]}")
            return 0

        with NLMClient() as client:
            for domain in domains_to_run:
                domain_data = notebook_data["domains"].get(
                    domain, {"current": None, "previous": None}
                )

                if (domain_data.get("current") or {}).get("id") is None:
                    nb_id = client.call_tool(
                        "notebook_create",
                        {"title": f"Second Brain — {domain} papers"},
                    )
                    domain_data["current"] = {
                        "id": nb_id,
                        "source_count": 0,
                        "created": today,
                        "pushed_paper_ids": [],
                    }
                    print(f"[{domain}] Created notebook: {nb_id}")

                if nb_mgr.needs_rotation(domain_data):
                    new_id = client.call_tool(
                        "notebook_create",
                        {"title": f"Second Brain — {domain} papers {today}"},
                    )
                    domain_data = nb_mgr.rotate(domain_data, new_id)
                    stats["rotations"].append({"domain": domain, "date": today})
                    print(f"[{domain}] Rotated → new notebook: {new_id}")

                new_papers = load_new_papers(domain, domain_data)
                for paper in new_papers:
                    text = (
                        f"Title: {paper['title']}\n"
                        f"Abstract: {paper['abstract']}\n"
                        f"Paper ID: {paper['paper_id']}"
                    )
                    client.call_tool("notebook_add_text", {
                        "notebook_id": domain_data["current"]["id"],
                        "content": text,
                        "title": paper["title"],
                    })
                    domain_data = nb_mgr.increment_source_count(domain_data, paper["paper_id"])
                    stats["papers_added"] += 1
                    print(f"[{domain}] Added: {paper['paper_id']}")

                notebook_data["domains"][domain] = domain_data
                stats["domains_processed"].append(domain)

                # Per-domain summary (spec §3.4 op-3)
                current_id = (domain_data.get("current") or {}).get("id")
                if current_id and new_papers:
                    summary = client.call_tool("notebook_describe", {"notebook_id": current_id})
                    week_num = date.today().isocalendar()[1]
                    summary_path = VAULT / "_inbox/raw/articles" / f"nlm-summary-{domain}-W{date.today().year}-{week_num:02d}.md"
                    summary_path.parent.mkdir(parents=True, exist_ok=True)
                    summary_path.write_text(
                        f"<!-- source-url: notebooklm:{current_id} -->\n\n{summary}\n",
                        encoding="utf-8",
                    )
                    print(f"[{domain}] Summary written → {summary_path.name}")

            tier_s_concepts = load_tier_s_concepts(CONCEPTS_DIR)
            print(f"\nGrounding {len(tier_s_concepts)} Tier S concept(s)...")

            for concept in tier_s_concepts:
                paper_id = concept["paper_id"]
                if not paper_id:
                    print(f"  SKIP (no paper_id): {concept['title'][:50]}")
                    continue

                domain = _infer_domain(paper_id)
                if not domain:
                    print(f"  SKIP (domain unknown): {paper_id}")
                    continue

                domain_data = notebook_data["domains"][domain]
                current_id = (domain_data.get("current") or {}).get("id")
                previous_id = (domain_data.get("previous") or {}).get("id")

                if not current_id:
                    print(f"  SKIP (no notebook for {domain}): {paper_id}")
                    continue

                responses = []
                used_ids = []
                for nb_id in filter(None, [current_id, previous_id]):
                    resp = client.call_tool("notebook_query", {
                        "notebook_id": nb_id,
                        "query": concept["title"],
                    })
                    responses.append(resp)
                    used_ids.append(nb_id)

                combined = "\n".join(responses)
                verdict, confidence = GroundingRouter.parse_verdict(combined)

                CONCEPTS_DIR.mkdir(parents=True, exist_ok=True)
                write_grounded_note(
                    paper_id=paper_id,
                    tier=concept["tier"],
                    source_chain=concept["source_chain"],
                    verdict=verdict,
                    confidence=confidence,
                    notebook_ids=used_ids,
                    nlm_response=combined,
                    output_dir=CONCEPTS_DIR,
                    today=today,
                )
                stats["concepts_grounded"] += 1
                print(f"  Grounded {paper_id}: {verdict} ({confidence:.2f})")

        cb.record_success(stats)
        print(f"\nDone. Papers added: {stats['papers_added']} | "
              f"Concepts grounded: {stats['concepts_grounded']} | "
              f"Rotations: {len(stats['rotations'])}")
        return 0

    except NLMClientError as exc:
        failures = cb.record_failure(str(exc))
        print(f"[ERROR] NLM error: {exc} (failure #{failures})", file=sys.stderr)
        return 1
    except Exception as exc:
        failures = cb.record_failure(f"unexpected: {exc}")
        print(f"[ERROR] Unexpected: {exc} (failure #{failures})", file=sys.stderr)
        return 1
    finally:
        # Always persist whatever state we accumulated (prevents double-push on retry
        # when an intermediate domain fails). Only in non-dry-run mode.
        if notebook_data is not None and not args.dry_run:
            try:
                nb_mgr.save(notebook_data)
            except Exception as save_exc:
                print(f"[WARN] Failed to persist notebook state: {save_exc}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
