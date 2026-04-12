# Sprint 2 — Track B NotebookLM Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate NotebookLM MCP as Track B enrichment layer — weekly paper ingestion, sliding-window notebooks, grounding verdicts for Tier S concepts, and circuit-breaker degradation.

**Architecture:** `notebooklm_weekly.py` runs weekly (Sunday, deadline 23:30) as a standalone script wrapping the `m4yk3ldev/notebooklm-mcp` MCP server via stdio JSON-RPC. It pushes paper abstracts to domain notebooks, grounds Tier S concepts via `notebook_query`, writes `B-{paper_id}-grounded.md` files to `_inbox/raw/concepts/`, and manages circuit-breaker state in `nlm-status.json`. The nightly agent then merges A+B tracks in Étape 2.

**Tech Stack:** Python 3.9+, Node.js (notebooklm-mcp via npx), MCP stdio JSON-RPC, PyYAML, pytest

---

## Prerequisites (manual — before first real run)

These cannot be automated. Complete before running the script with real data:

1. Create dedicated Google automation account (never personal)
2. Fork `m4yk3ldev/notebooklm-mcp` → audit source → pin commit SHA in package.json  
3. Install fork: `npm install -g git+https://github.com/<your-fork>/notebooklm-mcp#<commit-sha>`
4. Run auth setup: `notebooklm-mcp setup_auth` (creates `~/.notebooklm-mcp/auth.json`)
5. `chmod 600 ~/.notebooklm-mcp/auth.json`
6. Set env var: `export NLM_MCP_CMD=notebooklm-mcp` (add to `~/.zshenv`)

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `_meta/nlm-notebooks.json` | **Create** | Sliding-window notebook IDs + source counts per domain |
| `_logs/nlm-status.json` | **Create** | Circuit-breaker sentinel: complete/failed + consecutive_failures |
| `_inbox/overflow/.gitkeep` | **Create** | Overflow queue for cap-15 excess |
| `_inbox/quarantine/.gitkeep` | **Create** | Schema-invalid files awaiting manual review |
| `notebooklm_weekly.py` | **Create** | Track B orchestrator (caffeinate-safe, circuit-breaker aware) |
| `notebooklm-weekly.sh` | **Create** | Shell wrapper: caffeinate + PATH + timeout guard |
| `tests/test_notebooklm_weekly.py` | **Create** | Unit tests for all logic classes (NLMClient mocked) |
| `.nightly-prompt.md` | **Modify** | Étapes 0, 2, 5, 6 — B-track merge, grounding routing, enrichment_status, v6 schema |

---

## Task 1 — Bootstrap: sprint2 branch + sentinel files

**Files:**
- Create: `_meta/nlm-notebooks.json`
- Create: `_logs/nlm-status.json`
- Create: `_inbox/overflow/.gitkeep`
- Create: `_inbox/quarantine/.gitkeep`
- Create: `notebooklm-weekly.sh`

- [ ] **Step 1: Create sprint2 branch**

```bash
cd ~/Documents/Obsidian/KnowledgeBase
git checkout -b sprint2/track-b-notebooklm
```

Expected: `Switched to a new branch 'sprint2/track-b-notebooklm'`

- [ ] **Step 2: Create `_meta/nlm-notebooks.json`**

```bash
cat > ~/Documents/Obsidian/KnowledgeBase/_meta/nlm-notebooks.json << 'EOF'
{
  "schema_version": 1,
  "_comment": "Auto-managed by notebooklm_weekly.py. Do not edit manually.",
  "domains": {
    "ai": {
      "current": { "id": null, "source_count": 0, "created": null, "pushed_paper_ids": [] },
      "previous": null
    },
    "iot": {
      "current": { "id": null, "source_count": 0, "created": null, "pushed_paper_ids": [] },
      "previous": null
    },
    "cloud": {
      "current": { "id": null, "source_count": 0, "created": null, "pushed_paper_ids": [] },
      "previous": null
    },
    "ecommerce": {
      "current": { "id": null, "source_count": 0, "created": null, "pushed_paper_ids": [] },
      "previous": null
    }
  }
}
EOF
```

- [ ] **Step 3: Create `_logs/nlm-status.json`**

```bash
cat > ~/Documents/Obsidian/KnowledgeBase/_logs/nlm-status.json << 'EOF'
{
  "status": "not_initialized",
  "complete": false,
  "consecutive_failures": 0,
  "timestamp": null
}
EOF
```

- [ ] **Step 4: Create overflow and quarantine directories**

```bash
mkdir -p ~/Documents/Obsidian/KnowledgeBase/_inbox/overflow
mkdir -p ~/Documents/Obsidian/KnowledgeBase/_inbox/quarantine
touch ~/Documents/Obsidian/KnowledgeBase/_inbox/overflow/.gitkeep
touch ~/Documents/Obsidian/KnowledgeBase/_inbox/quarantine/.gitkeep
```

- [ ] **Step 5: Create `notebooklm-weekly.sh` wrapper**

```bash
cat > ~/Documents/Obsidian/KnowledgeBase/notebooklm-weekly.sh << 'EOF'
#!/bin/bash
# notebooklm-weekly.sh — Track B wrapper
# Runs weekly, deadline Sunday 23:30.
# Usage: bash notebooklm-weekly.sh [--domain DOMAIN] [--dry-run]
#
# Prerequisite: NLM_MCP_CMD set, auth.json configured
set -euo pipefail

VAULT="$HOME/Documents/Obsidian/KnowledgeBase"
LOG="$VAULT/_logs/nlm-weekly.log"
PYTHON="$(command -v python3)"

# Timeout guard: abort if past 23:30
HOUR=$(date +%H); MIN=$(date +%M)
if [ "$HOUR" -gt 23 ] || { [ "$HOUR" -eq 23 ] && [ "$MIN" -gt 30 ]; }; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Past 23:30 deadline — aborting" >> "$LOG"
  # Write incomplete sentinel so nightly agent skips B-track
  python3 -c "
import json, pathlib
p = pathlib.Path('$VAULT/_logs/nlm-status.json')
data = json.loads(p.read_text()) if p.exists() else {}
data.update({'complete': False, 'reason': 'deadline_exceeded'})
p.write_text(json.dumps(data, indent=2))
"
  exit 0
fi

echo "=== NLM Weekly $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" >> "$LOG"
caffeinate -i "$PYTHON" "$VAULT/notebooklm_weekly.py" "$@" >> "$LOG" 2>&1
echo "=== Done $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" >> "$LOG"
EOF
chmod +x ~/Documents/Obsidian/KnowledgeBase/notebooklm-weekly.sh
```

- [ ] **Step 6: Commit**

```bash
cd ~/Documents/Obsidian/KnowledgeBase
git add _meta/nlm-notebooks.json _logs/nlm-status.json \
    _inbox/overflow/.gitkeep _inbox/quarantine/.gitkeep \
    notebooklm-weekly.sh
git commit -m "feat(sprint2): bootstrap — nlm-notebooks.json, nlm-status.json, overflow/quarantine dirs"
```

---

## Task 2 — `notebooklm_weekly.py` + tests

**Files:**
- Create: `notebooklm_weekly.py`
- Create: `tests/test_notebooklm_weekly.py`

### Subtask 2A — `NotebookManager` tests + implementation

- [ ] **Step 1: Write failing tests for `NotebookManager`**

Create `tests/test_notebooklm_weekly.py`:

```python
"""Tests for notebooklm_weekly.py logic classes (NLMClient is mocked)."""
import json
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml


# ── NotebookManager ──────────────────────────────────────────────────────────

class TestNotebookManagerRotation:
    def _make_domain_data(self, source_count: int, pushed: list = None) -> dict:
        return {
            "current": {
                "id": "nb_test123",
                "source_count": source_count,
                "created": "2026-04-06",
                "pushed_paper_ids": pushed or [],
            },
            "previous": None,
        }

    def test_needs_rotation_at_45(self):
        from notebooklm_weekly import NotebookManager
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            mgr = NotebookManager(Path(f.name))
        assert mgr.needs_rotation(self._make_domain_data(45)) is True

    def test_needs_rotation_below_45(self):
        from notebooklm_weekly import NotebookManager
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            mgr = NotebookManager(Path(f.name))
        assert mgr.needs_rotation(self._make_domain_data(44)) is False

    def test_needs_rotation_no_current(self):
        from notebooklm_weekly import NotebookManager
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            mgr = NotebookManager(Path(f.name))
        assert mgr.needs_rotation({"current": None, "previous": None}) is False

    def test_rotate_moves_current_to_previous(self):
        from notebooklm_weekly import NotebookManager
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            mgr = NotebookManager(Path(f.name))
        old = self._make_domain_data(45, pushed=["arxiv:2401.001"])
        result = mgr.rotate(old, "nb_new456")
        assert result["previous"]["id"] == "nb_test123"
        assert result["current"]["id"] == "nb_new456"
        assert result["current"]["source_count"] == 0
        assert result["current"]["pushed_paper_ids"] == []

    def test_increment_source_count(self):
        from notebooklm_weekly import NotebookManager
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            mgr = NotebookManager(Path(f.name))
        domain_data = self._make_domain_data(3, pushed=["arxiv:2401.001"])
        result = mgr.increment_source_count(domain_data, "arxiv:2401.002")
        assert result["current"]["source_count"] == 4
        assert "arxiv:2401.002" in result["current"]["pushed_paper_ids"]
        assert "arxiv:2401.001" in result["current"]["pushed_paper_ids"]  # preserved

    def test_get_new_papers_excludes_pushed(self):
        from notebooklm_weekly import NotebookManager
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            mgr = NotebookManager(Path(f.name))
        domain_data = {
            "current": {"id": "nb1", "source_count": 2, "pushed_paper_ids": ["arxiv:2401.001", "s2:abc123"]},
            "previous": {"id": "nb0", "source_count": 45, "pushed_paper_ids": ["arxiv:2400.001"]},
        }
        all_ids = ["arxiv:2401.001", "arxiv:2401.002", "arxiv:2400.001", "s2:new999"]
        result = mgr.get_new_papers(domain_data, all_ids)
        assert result == ["arxiv:2401.002", "s2:new999"]

    def test_atomic_write_and_load(self):
        from notebooklm_weekly import NotebookManager
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nlm-notebooks.json"
            schema = {
                "schema_version": 1,
                "domains": {"ai": {"current": None, "previous": None}},
            }
            path.write_text(json.dumps(schema))
            mgr = NotebookManager(path)
            loaded = mgr.load()
            assert loaded["schema_version"] == 1
            loaded["domains"]["ai"]["current"] = {"id": "nb_abc", "source_count": 1, "pushed_paper_ids": []}
            mgr.save(loaded)
            reloaded = mgr.load()
            assert reloaded["domains"]["ai"]["current"]["id"] == "nb_abc"
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd ~/Documents/Obsidian/KnowledgeBase
python3 -m pytest tests/test_notebooklm_weekly.py::TestNotebookManagerRotation -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'notebooklm_weekly'`

- [ ] **Step 3: Create `notebooklm_weekly.py` with `NotebookManager`**

Create `notebooklm_weekly.py`:

```python
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

    Usage:
        with NLMClient() as client:
            result = client.call_tool("notebook_create", {"title": "My NB"})
    """

    def __init__(self, cmd: Optional[str] = None, timeout: int = 90):
        self.cmd = cmd or os.environ.get("NLM_MCP_CMD", "notebooklm-mcp")
        self.timeout = timeout
        self._proc: Optional[subprocess.Popen] = None
        self._next_id = 1
        self._response_q: queue.Queue = queue.Queue()
        self._reader_thread: Optional[threading.Thread] = None

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

    def _send(self, method: str, params: Optional[dict] = None, *, notify: bool = False) -> Optional[dict]:
        msg: dict = {"jsonrpc": "2.0", "method": method}
        msg_id = None
        if not notify:
            msg_id = self._next_id
            self._next_id += 1
            msg["id"] = msg_id
        if params is not None:
            msg["params"] = params
        self._proc.stdin.write(json.dumps(msg) + "\n")
        self._proc.stdin.flush()
        if notify:
            return None
        deadline = time.time() + self.timeout
        pending: list[dict] = []
        while time.time() < deadline:
            try:
                resp = self._response_q.get(timeout=1.0)
                if resp.get("id") == msg_id:
                    # Re-queue any messages we skipped
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
```

- [ ] **Step 4: Run NotebookManager tests — expect PASS**

```bash
cd ~/Documents/Obsidian/KnowledgeBase
python3 -m pytest tests/test_notebooklm_weekly.py::TestNotebookManagerRotation -v
```

Expected: `6 passed`

### Subtask 2B — `GroundingRouter` tests + implementation

- [ ] **Step 5: Add `GroundingRouter` tests**

Append to `tests/test_notebooklm_weekly.py`:

```python
# ── GroundingRouter ───────────────────────────────────────────────────────────

class TestGroundingRouter:
    def test_supported_with_multiple_sources(self):
        from notebooklm_weekly import GroundingRouter
        text = (
            "The evidence strongly supports this claim. [Source 1] demonstrates "
            "the effect clearly, consistent with prior work. [Source 2] corroborates "
            "these findings and confirms the hypothesis."
        )
        verdict, confidence = GroundingRouter.parse_verdict(text)
        assert verdict == "supported"
        assert confidence >= 0.65

    def test_disputed_with_contradictions(self):
        from notebooklm_weekly import GroundingRouter
        text = (
            "While [Source 1] supports this, [Source 2] contradicts the main claim. "
            "The evidence is inconsistent across sources, with mixed results."
        )
        verdict, confidence = GroundingRouter.parse_verdict(text)
        assert verdict == "disputed"
        assert confidence < 0.5

    def test_partially_supported_single_source(self):
        from notebooklm_weekly import GroundingRouter
        text = "According to the source, the claim is partially supported by [Source 1]."
        verdict, confidence = GroundingRouter.parse_verdict(text)
        assert verdict in ("partially_supported", "supported")

    def test_insufficient_evidence_empty(self):
        from notebooklm_weekly import GroundingRouter
        verdict, confidence = GroundingRouter.parse_verdict("")
        assert verdict == "insufficient_evidence"
        assert confidence == 0.0

    def test_insufficient_evidence_no_sources(self):
        from notebooklm_weekly import GroundingRouter
        text = "The topic is interesting but no sources were found in the notebook."
        verdict, confidence = GroundingRouter.parse_verdict(text)
        assert verdict == "insufficient_evidence"

    def test_confidence_is_float_between_0_and_1(self):
        from notebooklm_weekly import GroundingRouter
        for text in [
            "Strongly supports [Source 1] confirms shows evidence [Source 2]",
            "contradicts however contrary conflicts",
            "",
            "according to shows [Source 1]",
        ]:
            _, conf = GroundingRouter.parse_verdict(text)
            assert 0.0 <= conf <= 1.0, f"conf={conf} out of range for: {text!r}"
```

- [ ] **Step 6: Run GroundingRouter tests — expect FAIL**

```bash
cd ~/Documents/Obsidian/KnowledgeBase
python3 -m pytest tests/test_notebooklm_weekly.py::TestGroundingRouter -v 2>&1 | tail -10
```

Expected: `AttributeError: module 'notebooklm_weekly' has no attribute 'GroundingRouter'`

- [ ] **Step 7: Add `GroundingRouter` to `notebooklm_weekly.py`**

Append after the `NotebookManager` class:

```python
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
```

- [ ] **Step 8: Run GroundingRouter tests — expect PASS**

```bash
cd ~/Documents/Obsidian/KnowledgeBase
python3 -m pytest tests/test_notebooklm_weekly.py::TestGroundingRouter -v
```

Expected: `6 passed`

### Subtask 2C — `CircuitBreaker` tests + implementation

- [ ] **Step 9: Add `CircuitBreaker` tests**

Append to `tests/test_notebooklm_weekly.py`:

```python
# ── CircuitBreaker ────────────────────────────────────────────────────────────

class TestCircuitBreaker:
    def test_record_success_resets_failures(self):
        from notebooklm_weekly import CircuitBreaker
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nlm-status.json"
            # Start with existing failures
            path.write_text(json.dumps({"consecutive_failures": 3, "complete": False}))
            cb = CircuitBreaker(path)
            cb.record_success({"papers_added": 5})
            loaded = json.loads(path.read_text())
            assert loaded["complete"] is True
            assert loaded["consecutive_failures"] == 0
            assert loaded["status"] == "complete"
            assert "timestamp" in loaded
            assert loaded["papers_added"] == 5

    def test_record_failure_increments_counter(self):
        from notebooklm_weekly import CircuitBreaker
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nlm-status.json"
            path.write_text(json.dumps({"consecutive_failures": 1}))
            cb = CircuitBreaker(path)
            failures = cb.record_failure("auth_error")
            assert failures == 2
            loaded = json.loads(path.read_text())
            assert loaded["consecutive_failures"] == 2
            assert loaded["complete"] is False
            assert loaded["reason"] == "auth_error"

    def test_load_missing_file_returns_defaults(self):
        from notebooklm_weekly import CircuitBreaker
        with tempfile.TemporaryDirectory() as tmpdir:
            cb = CircuitBreaker(Path(tmpdir) / "absent.json")
            state = cb.load()
            assert state["consecutive_failures"] == 0
            assert state["status"] == "not_initialized"

    def test_atomic_write_no_partial_state(self):
        from notebooklm_weekly import CircuitBreaker
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nlm-status.json"
            cb = CircuitBreaker(path)
            cb.record_success({"concepts_grounded": 3})
            # No .tmp file should remain
            assert not path.with_suffix(".json.tmp").exists()
```

- [ ] **Step 10: Run CircuitBreaker tests — expect FAIL**

```bash
cd ~/Documents/Obsidian/KnowledgeBase
python3 -m pytest tests/test_notebooklm_weekly.py::TestCircuitBreaker -v 2>&1 | tail -5
```

Expected: `AttributeError: module 'notebooklm_weekly' has no attribute 'CircuitBreaker'`

- [ ] **Step 11: Add `CircuitBreaker` to `notebooklm_weekly.py`**

Append after `GroundingRouter`:

```python
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
```

- [ ] **Step 12: Run CircuitBreaker tests — expect PASS**

```bash
cd ~/Documents/Obsidian/KnowledgeBase
python3 -m pytest tests/test_notebooklm_weekly.py::TestCircuitBreaker -v
```

Expected: `4 passed`

### Subtask 2D — `write_grounded_note` + `load_tier_s_concepts` tests + implementation

- [ ] **Step 13: Add `write_grounded_note` and `load_tier_s_concepts` tests**

Append to `tests/test_notebooklm_weekly.py`:

```python
# ── write_grounded_note ───────────────────────────────────────────────────────

class TestWriteGroundedNote:
    def _write(self, tmpdir, paper_id="arxiv:2401.12345", verdict="supported", confidence=0.87):
        from notebooklm_weekly import write_grounded_note
        return write_grounded_note(
            paper_id=paper_id,
            tier="S",
            source_chain=["origin: https://arxiv.org/abs/2401.12345", "via: abstract"],
            verdict=verdict,
            confidence=confidence,
            notebook_ids=["nb_abc123", "nb_xyz789"],
            nlm_response="The sources confirm this claim strongly.",
            output_dir=Path(tmpdir),
            today="2026-04-13",
        )

    def test_filename_uses_sanitized_paper_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write(tmpdir)
            assert path.name == "B-arxiv-2401-12345-grounded.md"

    def test_s2_paper_id_sanitized(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            from notebooklm_weekly import write_grounded_note
            path = write_grounded_note(
                paper_id="s2:abc1234567890abc",
                tier="S",
                source_chain=["origin: https://example.com", "via: abstract"],
                verdict="partially_supported",
                confidence=0.60,
                notebook_ids=["nb_abc"],
                nlm_response="Partial evidence found.",
                output_dir=Path(tmpdir),
                today="2026-04-13",
            )
            assert path.name == "B-s2-abc1234567890abc-grounded.md"

    def test_frontmatter_contains_nlm_grounding(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write(tmpdir)
            text = path.read_text()
            fm = yaml.safe_load(text.split("---")[1])
            assert fm["nlm_grounding"]["verdict"] == "supported"
            assert fm["nlm_grounding"]["confidence"] == 0.87
            assert "nb_abc123" in fm["nlm_grounding"]["notebook_ids"]

    def test_frontmatter_required_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write(tmpdir)
            text = path.read_text()
            fm = yaml.safe_load(text.split("---")[1])
            for field in ("type", "maturity", "tier", "created", "paper_id", "source_chain"):
                assert field in fm, f"Missing required field: {field}"
            assert fm["maturity"] == "fleeting"
            assert fm["type"] == "concept"

    def test_disputed_adds_review_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write(tmpdir, verdict="disputed", confidence=0.30)
            content = path.read_text()
            assert "<!-- review-flag: nlm-disputed -->" in content

    def test_non_disputed_no_review_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write(tmpdir, verdict="supported", confidence=0.90)
            content = path.read_text()
            assert "review-flag: nlm-disputed" not in content


# ── load_tier_s_concepts ──────────────────────────────────────────────────────

class TestLoadTierSConcepts:
    def _make_concept_file(self, tmpdir, paper_id: str, tier: str) -> Path:
        pid_sanitized = paper_id.replace(":", "-").replace(".", "-")
        path = Path(tmpdir) / f"A-{pid_sanitized}-1.md"
        fm = {
            "type": "concept",
            "maturity": "fleeting",
            "tier": tier,
            "created": "2026-04-13",
            "paper_id": paper_id,
            "source_chain": [f"origin: https://arxiv.org/abs/2401.001", "via: abstract"],
        }
        path.write_text(
            f"---\n{yaml.dump(fm, allow_unicode=True)}---\n\n# Titre test\n\nContenu.\n",
            encoding="utf-8",
        )
        return path

    def test_loads_only_tier_s(self):
        from notebooklm_weekly import load_tier_s_concepts
        with tempfile.TemporaryDirectory() as tmpdir:
            self._make_concept_file(tmpdir, "arxiv:2401.001", "S")
            self._make_concept_file(tmpdir, "arxiv:2401.002", "A")
            self._make_concept_file(tmpdir, "arxiv:2401.003", "S")
            results = load_tier_s_concepts(Path(tmpdir))
            assert len(results) == 2
            paper_ids = {r["paper_id"] for r in results}
            assert "arxiv:2401.001" in paper_ids
            assert "arxiv:2401.003" in paper_ids

    def test_extracts_title(self):
        from notebooklm_weekly import load_tier_s_concepts
        with tempfile.TemporaryDirectory() as tmpdir:
            self._make_concept_file(tmpdir, "arxiv:2401.001", "S")
            results = load_tier_s_concepts(Path(tmpdir))
            assert results[0]["title"] == "Titre test"

    def test_empty_dir_returns_empty(self):
        from notebooklm_weekly import load_tier_s_concepts
        with tempfile.TemporaryDirectory() as tmpdir:
            assert load_tier_s_concepts(Path(tmpdir)) == []
```

- [ ] **Step 14: Run these tests — expect FAIL**

```bash
cd ~/Documents/Obsidian/KnowledgeBase
python3 -m pytest tests/test_notebooklm_weekly.py::TestWriteGroundedNote tests/test_notebooklm_weekly.py::TestLoadTierSConcepts -v 2>&1 | tail -10
```

Expected: `AttributeError: module 'notebooklm_weekly' has no attribute 'write_grounded_note'`

- [ ] **Step 15: Add `write_grounded_note` and `load_tier_s_concepts` to `notebooklm_weekly.py`**

Append after `CircuitBreaker`:

```python
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
    """
    Find which domain this paper belongs to by scanning papers directories.
    Checks current inbox, then _processed.
    """
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
```

- [ ] **Step 16: Run all tests — expect PASS**

```bash
cd ~/Documents/Obsidian/KnowledgeBase
python3 -m pytest tests/test_notebooklm_weekly.py -v
```

Expected: `26 passed`

### Subtask 2E — `main()` + dry-run integration

- [ ] **Step 17: Add `main()` to `notebooklm_weekly.py`**

Append at end of file:

```python
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

    try:
        notebook_data = nb_mgr.load()

        if args.dry_run:
            # Dry-run: report what would happen without touching NLM
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

                # Ensure notebook exists for this domain
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

                # Rotation if needed
                if nb_mgr.needs_rotation(domain_data):
                    new_id = client.call_tool(
                        "notebook_create",
                        {"title": f"Second Brain — {domain} papers {today}"},
                    )
                    domain_data = nb_mgr.rotate(domain_data, new_id)
                    stats["rotations"].append({"domain": domain, "date": today})
                    print(f"[{domain}] Rotated → new notebook: {new_id}")

                # Push new papers
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

                # Generate per-domain summary (spec §3.4 op-3)
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

            # Ground Tier S concepts
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

                # Query current + previous (sliding window)
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

        # Persist notebook state
        nb_mgr.save(notebook_data)
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


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 18: Run dry-run to verify import and argument parsing**

```bash
cd ~/Documents/Obsidian/KnowledgeBase
python3 notebooklm_weekly.py --dry-run 2>&1 | head -20
```

Expected: Output listing domains with paper counts, no error/traceback.

- [ ] **Step 19: Run full test suite**

```bash
cd ~/Documents/Obsidian/KnowledgeBase
python3 -m pytest tests/ -v 2>&1 | tail -15
```

Expected: `46 passed` (20 from Sprint 1 + 26 new)

- [ ] **Step 20: Commit**

```bash
cd ~/Documents/Obsidian/KnowledgeBase
git add notebooklm_weekly.py tests/test_notebooklm_weekly.py
git commit -m "feat(track-b): notebooklm_weekly.py — NLMClient, NotebookManager, GroundingRouter, CircuitBreaker + 23 tests"
```

---

## Task 3 — `.nightly-prompt.md` Track B integration

**Files:**
- Modify: `.nightly-prompt.md` (Étapes 0, 2, 5, 6)

This task has no Python code and therefore no automated tests. Changes are verified by reading the file and checking for correct sections.

### Subtask 3A — Étape 0: activate B-track from nlm-status.json

- [ ] **Step 1: Update Étape 0 Step 4 to check nlm-status.json**

In `.nightly-prompt.md`, find the current Step 4 in Étape 0 (batch_job_id check). Replace the entire block starting with `4. **batch_job_id check**` with:

```markdown
4. **B-track activation check** : lire `_logs/nlm-status.json`.
   - Si `complete: true` → activer le B-track intake à l'Étape 2 (`track_b_active = true`)
   - Si `complete: false` ou fichier absent → `track_b_active = false`, skip B-track intake
   - Logger `track_b_active` dans `_logs/last-nightly.json` sous `enrichment_status.track_b_active`

5. **batch_job_id check** : si `_logs/batch_jobs.json` contient des entrées sans fichiers `A-*.md` correspondants dans `_inbox/raw/concepts/` → logger un warning dans `_logs/last-nightly.json`, continuer.

6. **Inbox check** : compter les fichiers dans `_inbox/` (hors `_processed/`, `overflow/`).
   - Si inbox vide ET lint effectué il y a moins de 3 jours → écrire dans `_logs/last-nightly.json` :
     ```json
     {"status": "skipped", "reason": "no work", "last_run": "TIMESTAMP_ISO"}
     ```
     Puis **arrêter le run**.
```

Note: the original Étape 0 had 5 steps (1 overflow, 2 ceiling, 3 fleeting, 4 batch_job_id, 5 inbox). After this edit it has 6 steps (1 overflow, 2 ceiling, 3 fleeting, 4 B-track activation, 5 batch_job_id, 6 inbox).

- [ ] **Step 2: Verify Étape 0 step count**

```bash
grep -c "^\d\+\. \*\*" ~/Documents/Obsidian/KnowledgeBase/.nightly-prompt.md || \
grep -n "^[1-6]\. \*\*" ~/Documents/Obsidian/KnowledgeBase/.nightly-prompt.md | head -20
```

Expected: 6 numbered items in Étape 0.

### Subtask 3B — Étape 2: B-track section (merge, grounding routing, quarantine)

- [ ] **Step 3: Add section 2C to Étape 2**

In `.nightly-prompt.md`, find the end of section `#### 2B` (the line ending with `Si \`_inbox/raw/\` vide ou tous traités → Étape 3.`). Insert **before** that final line a new section:

```markdown
#### 2C — `_inbox/raw/concepts/B-*.md` (Track B grounded notes)

Traiter uniquement si `track_b_active = true` (déterminé à l'Étape 0).
Ces fichiers contiennent un frontmatter `nlm_grounding` produit par `notebooklm_weekly.py`.
Cap partagé : les fichiers B-track comptent dans le même cap de 15 que les A-track.

Pour chaque fichier `B-{paper_id_sanitized}-grounded.md` dans `_inbox/raw/concepts/` :

1. **Validation frontmatter** : vérifier `type`, `tier`, `paper_id`, `source_chain`, `nlm_grounding.verdict`.
   - Si un champ REQUIRED est absent → déplacer vers `_inbox/quarantine/YYYY-MM-DD-{fichier}` avec message :
     ```
     # Quarantined: {fichier}
     Raison: champ requis manquant — {champ}
     Date: YYYY-MM-DD
     ```
     Skip ce fichier.

2. **Vérifier si un A-track correspondant existe** (même `paper_id`) :
   - **Cas A+B (merge)** : si `A-{paper_id_sanitized}-*.md` existe dans `_inbox/raw/concepts/` OU déjà dans le vault :
     - A-track gagne (contenu principal)
     - Enrichir la note A-track avec le champ `nlm_grounding` du fichier B
     - Appliquer le routing grounding verdict (voir ci-dessous) sur la note A
     - Supprimer le fichier B (il a été absorbé dans A)
   - **Cas B standalone** : si aucun A correspondant :
     - Atomiser le contenu NLM en note vault via le prompt suivant :
       ```
       Dériver le claim principal de cette réponse NLM en une note vault française.
       Ne pas traduire mot-à-mot. Titre déclaratif obligatoire (phrase affirmative testable).
       Si nlm_grounding.verdict = 'disputed' : ajouter <!-- review-flag: nlm-disputed -->
       Liens non résolus → <!-- candidate: X --> jamais de wikilinks directs.
       Respecter le template de note obligatoire (type, maturity: fleeting, tier, source_chain).
       ```
     - Résultat → note vault comme pour 2A

3. **Routing grounding verdict** (appliqué à toute note portant nlm_grounding) :
   - `supported` → note éligible à promotion standard, aucune modification
   - `partially_supported` → note éligible, aucune modification
   - `disputed` → forcer `maturity: fleeting` + ajouter `<!-- review-flag: nlm-disputed -->` dans le corps
   - `insufficient_evidence` → traiter comme si pas de grounding (ignorer nlm_grounding)

4. Appender dans `_meta/LOG.md` :
   `## [YYYY-MM-DD] ingest | raw/concepts/B-xxx.md → merged into A-xxx / 1 note (nlm-grounded)`
5. Déplacer le fichier B source → `_inbox/raw/concepts/_processed/YYYY-MM-DD-B-xxx.md`
```

- [ ] **Step 4: Verify 2C section was added**

```bash
grep -n "2C\|B-track\|nlm_grounding\|quarantine" ~/Documents/Obsidian/KnowledgeBase/.nightly-prompt.md | head -15
```

Expected: Lines with `2C`, `B-track`, `nlm_grounding`, `quarantine` visible.

### Subtask 3C — Étape 5: enrichment_status + ALERT

- [ ] **Step 5: Update Étape 5 with enrichment_status tracking**

In `.nightly-prompt.md`, find the Étape 5 section. After the line `**INDEX diff (optimisation budget) :**`, insert a new block at the top of Étape 5:

```markdown
**Enrichment status (Track B) :**

1. Lire `_logs/nlm-status.json` :
   - `consecutive_failures` = valeur dans le fichier (0 si absent)
   - `last_nlm_success` = `timestamp` du dernier run avec `complete: true` (null si jamais)
   - `track_b_active` = `complete: true` (boolean)

2. Si `consecutive_failures >= 2` → créer `_inbox/ALERT-nlm-degraded.md` si absent :
   ```markdown
   # ALERT — NotebookLM Dégradé
   Date: YYYY-MM-DD
   Raison: {consecutive_failures} runs Track B consécutifs ont échoué.
   Action requise : ré-authentification manuelle.
   Dernière réussite : {last_nlm_success}
   ```

3. Mettre à jour `enrichment_status` dans `_logs/last-nightly.json` :
   ```json
   {
     "track_b_active": <bool>,
     "last_nlm_success": "<ISO8601 ou null>",
     "consecutive_failures": <int>,
     "notebook_rotations": []
   }
   ```
   (Les `notebook_rotations` sont lues depuis `nlm-status.json` si présentes.)

```

- [ ] **Step 6: Verify enrichment_status section exists**

```bash
grep -n "enrichment_status\|consecutive_failures\|ALERT-nlm" ~/Documents/Obsidian/KnowledgeBase/.nightly-prompt.md
```

Expected: At least 3 matches in Étape 5 zone.

### Subtask 3D — Étape 6: v6 JSON schema

- [ ] **Step 7: Update Étape 6 last-nightly.json to v6 schema**

In `.nightly-prompt.md`, find the Étape 6 `last-nightly.json` JSON block (starts with `"status": "success"`). Replace the entire JSON block with:

```json
{
  "status": "success|partial|failed",
  "last_run": "ISO8601",
  "last_lint_date": "ISO8601",
  "notes_added": 0,
  "tokens_used": 0,
  "tier_distribution": {"S": 0, "A": 0, "B": 0},
  "errors": [],
  "enrichment_status": {
    "track_b_active": false,
    "last_nlm_success": null,
    "consecutive_failures": 0,
    "notebook_rotations": []
  },
  "health": {
    "vault_note_count": 0,
    "backlog_inbox": 0,
    "overflow_count": 0,
    "fleeting_count": 0,
    "orphan_count": 0,
    "oldest_unreviewed_days": 0,
    "bridge_drafts_pending": 0,
    "ceiling_pct": 0.0
  }
}
```

Note: `vault_note_count` was already added in Sprint 1. New fields: `tokens_used`, `tier_distribution`, `enrichment_status`, `overflow_count`, `ceiling_pct`.

- [ ] **Step 8: Verify v6 schema fields**

```bash
grep -n "enrichment_status\|tier_distribution\|overflow_count\|ceiling_pct\|tokens_used" \
  ~/Documents/Obsidian/KnowledgeBase/.nightly-prompt.md | grep -v "Étape 5"
```

Expected: All 5 fields visible in the Étape 6 JSON block.

- [ ] **Step 9: Sanity-check section count**

```bash
grep -c "^### Étape" ~/Documents/Obsidian/KnowledgeBase/.nightly-prompt.md
```

Expected: `6` (Étapes 0-6 except no Étape header for Étape 0... actually check for the exact count you expect)

```bash
grep "^### Étape" ~/Documents/Obsidian/KnowledgeBase/.nightly-prompt.md
```

Expected: Lines for Étapes 0, 1, 2, 3, 4, 5, 6.

- [ ] **Step 10: Run full test suite to confirm no regressions**

```bash
cd ~/Documents/Obsidian/KnowledgeBase
python3 -m pytest tests/ -v 2>&1 | tail -5
```

Expected: `43 passed`

- [ ] **Step 11: Commit**

```bash
cd ~/Documents/Obsidian/KnowledgeBase
git add .nightly-prompt.md
git commit -m "feat(nightly-prompt): Track B intake (2C), enrichment_status, ALERT-nlm-degraded, v6 health schema"
```

---

## Final Validation

- [ ] **Step 1: Run dry-run full pipeline check**

```bash
cd ~/Documents/Obsidian/KnowledgeBase
python3 notebooklm_weekly.py --dry-run
python3 paper_synthesizer.py --dry-run
python3 -m pytest tests/ -v 2>&1 | tail -5
```

Expected: No tracebacks. `46 passed`.

- [ ] **Step 2: Verify all sentinel files exist with valid JSON**

```bash
python3 -c "
import json
from pathlib import Path
vault = Path.home() / 'Documents/Obsidian/KnowledgeBase'
for f in ['_meta/nlm-notebooks.json', '_logs/nlm-status.json']:
    data = json.loads((vault / f).read_text())
    print(f'OK: {f} — keys: {list(data.keys())}')
"
```

Expected:
```
OK: _meta/nlm-notebooks.json — keys: ['schema_version', '_comment', 'domains']
OK: _logs/nlm-status.json — keys: ['status', 'complete', 'consecutive_failures', 'timestamp']
```

- [ ] **Step 3: Verify overflow and quarantine dirs exist**

```bash
ls ~/Documents/Obsidian/KnowledgeBase/_inbox/overflow/ \
   ~/Documents/Obsidian/KnowledgeBase/_inbox/quarantine/
```

Expected: `.gitkeep` in each.

- [ ] **Step 4: Tag sprint2-complete**

```bash
cd ~/Documents/Obsidian/KnowledgeBase
git log --oneline -6
git tag sprint2-complete
```

---

## Parallelization Note

Tasks 1 and 2 are independent (different files) — run in parallel.  
Task 3 depends on Tasks 1+2 (uses paths created in Task 1, tests paths via pytest in Step 10).
