#!/usr/bin/env python3
"""
paper_synthesizer.py — Weekly paper synthesis pipeline
Runs after corpus_collector.py (Saturday/Sunday)
Uses Anthropic Claude Haiku Batch API to extract atomic concepts from scientific papers.

Requirements:
  pip install anthropic

Environment:
  ANTHROPIC_API_KEY — Anthropic API key

Usage:
  python3 paper_synthesizer.py [--domain DOMAIN] [--dry-run] [--week N]
  python3 paper_synthesizer.py --domain ai --dry-run
  python3 paper_synthesizer.py --week 16 --min-tier A
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import anthropic

# ── Constants ─────────────────────────────────────────────────────────────────

VAULT_ROOT = Path(__file__).parent
PAPERS_DIR = VAULT_ROOT / "_inbox" / "raw" / "papers"
CONCEPTS_DIR = VAULT_ROOT / "_inbox" / "raw" / "concepts"
RESEARCH_DIR = VAULT_ROOT / "universal" / "research"
LOGS_DIR = VAULT_ROOT / "_logs"

DOMAINS = ["ai", "iot", "cloud", "ecommerce"]

TIER_ORDER = {"S": 3, "A": 2, "B": 1}

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS_CONCEPTS = 1024
MAX_TOKENS_DIGEST = 1500

BATCH_JOBS_FILE = LOGS_DIR / "batch_jobs.json"

# ── Prompts ───────────────────────────────────────────────────────────────────

# System prompt — stable, mis en cache (cache_control: ephemeral)
SYSTEM_PROMPT = """\
Tu es un extracteur de concepts scientifiques pour un second brain Obsidian.
Projets actifs : gpparts (e-commerce Next.js), second-brain (PKM automatisé).

RÈGLES ABSOLUES :
1. DÉRIVER LE CLAIM, NE PAS TRADUIRE. Reformule dans tes propres mots. JAMAIS plus de 5 mots consécutifs de la source.
2. MITOSE COGNITIVE : produis une liste numérotée de concepts AVANT les blocs JSON, puis 1 bloc JSON par concept.
3. TITRE DÉCLARATIF : phrase affirmative testable en français (peut être vraie ou fausse).
4. TIER ASSIGNMENT :
   - S : directement applicable à gpparts ou second-brain aujourd'hui
   - A : concept solide à valeur future documentée
   - B : référence intéressante, 1 ligne essence suffit
   - Ignorer contributions trop théoriques sans application pratique

Pour CHAQUE concept, produis un bloc JSON :
```json
{
  "concept_title": "Phrase affirmative testable en français",
  "tier": "S|A|B",
  "tier_reason": "Lien concret avec gpparts/second-brain ou valeur générale",
  "essence": "2-3 lignes reformulées — JAMAIS copiées de l'abstract",
  "detail": "Explication complète reformulée dans tes propres mots",
  "tags": ["tag1", "tag2"],
  "simple_explanation": "Explication en 15 mots max pour un enfant de 12 ans",
  "paper_id": "à remplir depuis le contexte",
  "source_url": "à remplir depuis le contexte"
}
```

Minimum 1 concept, maximum 4 concepts par paper.
Produis UNIQUEMENT la liste numérotée puis les blocs JSON, séparés par des lignes vides.\
"""

# User prompt template — varie par paper (non caché)
USER_PROMPT_TEMPLATE = """\
Paper à analyser :
Titre : {title}
Domaine : {domain}
paper_id : {paper_id}
Source URL : {source_url}

Contenu :
{content}

Extrait les concepts clés sous forme de blocs JSON selon les règles système.\
"""

DIGEST_PROMPT = """Tu crées une note de littérature pour un vault Obsidian.

Semaine : W{week_num}
Domaine : {domain}
Papers analysés : {paper_titles}

Résumés des concepts extraits :
{concepts_summary}

## Tâche

Crée une synthèse narrative de 300-400 mots qui :
1. Identifie les tendances émergentes de la semaine dans ce domaine
2. Note les connexions entre les papers (convergences, contradictions)
3. Signale les 1-2 concepts les plus pertinents pour les projets gpparts/second-brain

Format de sortie : markdown direct, pas de JSON. Titre H2 "## Tendances W{week_num}", puis H3 sections."""


def sanitize_paper_id(paper_id: str) -> str:
    """Transforme un paper_id en segment de nom de fichier sûr.

    'arxiv:2401.12345' → 'arxiv-2401-12345'
    's2:abc123'        → 's2-abc123'
    """
    return paper_id.replace(":", "-").replace(".", "-")


# ── Frontmatter / paper parsing ───────────────────────────────────────────────

def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Extract YAML frontmatter and body from markdown text.
    Returns (meta_dict, body_text). meta_dict is empty if no frontmatter found."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    yaml_block = text[3:end].strip()
    body = text[end + 4:].strip()
    meta = {}
    for line in yaml_block.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            meta[key.strip()] = val.strip()
    return meta, body


def load_papers(domain: str) -> list[dict]:
    """Load all unprocessed papers for a domain. Returns list of paper dicts."""
    domain_dir = PAPERS_DIR / domain
    if not domain_dir.exists():
        return []

    papers = []
    for md_file in sorted(domain_dir.glob("*.md")):
        # Skip anything inside _processed/
        if "_processed" in md_file.parts:
            continue
        try:
            raw = md_file.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"  [WARN] Cannot read {md_file.name}: {exc}", file=sys.stderr)
            continue

        meta, body = parse_frontmatter(raw)
        if not meta:
            print(f"  [WARN] No frontmatter in {md_file.name} — skipping", file=sys.stderr)
            continue

        papers.append({
            "path": md_file,
            "domain": meta.get("domain", domain),
            "arxiv_id": meta.get("arxiv_id", ""),
            "source_url": meta.get("source_url", ""),
            "title": _extract_title(body),
            "content": raw,
        })

    return papers


def _extract_title(body: str) -> str:
    """Pull the first H1 line from the markdown body."""
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return "Untitled"


# ── Slug / file naming ────────────────────────────────────────────────────────

def slugify(text: str, max_len: int = 60) -> str:
    """Convert a concept title to a kebab-case filename-safe slug."""
    text = text.lower()
    text = re.sub(r"[àáâãäå]", "a", text)
    text = re.sub(r"[èéêë]", "e", text)
    text = re.sub(r"[ìíîï]", "i", text)
    text = re.sub(r"[òóôõö]", "o", text)
    text = re.sub(r"[ùúûü]", "u", text)
    text = re.sub(r"[ç]", "c", text)
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s]+", "-", text.strip())
    text = re.sub(r"-+", "-", text)
    return text[:max_len].rstrip("-")


# ── Concept JSON parsing ──────────────────────────────────────────────────────

def parse_concepts_from_text(text: str) -> list[dict]:
    """Extract JSON concept blocks from LLM output. Tolerant of extra prose."""
    concepts = []
    # Find all JSON objects in the text
    for match in re.finditer(r"\{[^{}]*\}", text, re.DOTALL):
        raw = match.group(0)
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            # Try to fix common issues: trailing commas
            cleaned = re.sub(r",\s*([}\]])", r"\1", raw)
            try:
                obj = json.loads(cleaned)
            except json.JSONDecodeError:
                continue
        # Validate required keys
        if all(k in obj for k in ("concept_title", "tier", "essence")):
            concepts.append(obj)
    return concepts


# ── Note / digest writers ─────────────────────────────────────────────────────

def write_concept_note(concept: dict, domain: str, week_num: int, today: str,
                       index: int = 1) -> Path:
    """Write a pre-note atomic file to _inbox/raw/concepts/. Returns the path.

    Naming convention : A-{paper_id_sanitized}-{n}.md
    Ex: A-arxiv-2401-12345-1.md, A-s2-abc1234567890abc-2.md
    """
    CONCEPTS_DIR.mkdir(parents=True, exist_ok=True)

    paper_id = concept.get("paper_id", "")
    if not paper_id:
        # paper_id absent = upstream frontmatter corruption; log and use source_url hash as fallback
        source_url = concept.get("source_url", "")
        fallback_base = hashlib.md5(
            source_url.encode("utf-8") if source_url else b"unknown",
            usedforsecurity=False,
        ).hexdigest()[:12]
        print(
            f"  [WARN] write_concept_note: missing paper_id for '{concept.get('concept_title','?')[:40]}'"
            f" — using fallback key {fallback_base}",
            file=sys.stderr,
        )
        pid_sanitized = f"unknown-{fallback_base}"
    else:
        pid_sanitized = sanitize_paper_id(paper_id)
    out_path = CONCEPTS_DIR / f"A-{pid_sanitized}-{index}.md"

    tier = concept.get("tier", "B")
    source_url = concept.get("source_url", "")
    simple_explanation = concept.get("simple_explanation", "")
    tags = concept.get("tags", [])
    tag_str = " ".join(f"#{t}" for t in [domain] + tags)

    content = f"""---
type: concept
maturity: fleeting
tier: {tier}
created: {today}
source_chain:
  - "origin: {source_url}"
  - "via: paper_synthesizer.py W{week_num}"
simple_explanation: "{simple_explanation}"
---

# {concept.get("concept_title", "Untitled")}

Tags: {tag_str}

## Essentiel
{concept.get("essence", "")}

## Détail
{concept.get("detail", "")}

## Liens

<!-- generated: {today} | synthesizer: paper_synthesizer.py -->
"""
    out_path.write_text(content, encoding="utf-8")
    return out_path


def write_digest(domain: str, week_num: int, digest_content: str,
                 paper_titles: list[str], papers: list[dict], today: str) -> Path:
    """Write a literature digest to universal/research/. Returns the path."""
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)

    out_path = RESEARCH_DIR / f"digest-{domain}-W{week_num}.md"

    # Build paper sources list with links
    sources_lines = []
    for p in papers:
        url = p.get("source_url", "")
        title = p.get("title", "Unknown")
        if url:
            sources_lines.append(f"- [{title}]({url})")
        else:
            sources_lines.append(f"- {title}")
    sources_block = "\n".join(sources_lines)

    content = f"""---
type: literature
maturity: fleeting
tier: A
created: {today}
source_chain:
  - "origin: arXiv papers W{week_num}"
  - "via: paper_synthesizer.py"
papers_count: {len(papers)}
domain: {domain}
---

# Digest {domain} W{week_num}

Tags: #{domain} #digest #literature

{digest_content}

## Papers sources
{sources_block}

<!-- generated: {today} -->
"""
    out_path.write_text(content, encoding="utf-8")
    return out_path


# ── Batch job recovery ────────────────────────────────────────────────────────

def save_batch_job(domain: str, batch_id: str) -> None:
    """Persiste le batch_id pour recovery en cas de crash."""
    LOGS_DIR.mkdir(exist_ok=True)
    jobs: dict = {}
    if BATCH_JOBS_FILE.exists():
        try:
            jobs = json.loads(BATCH_JOBS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    jobs[domain] = {"batch_id": batch_id, "submitted_at": datetime.utcnow().isoformat()}
    BATCH_JOBS_FILE.write_text(json.dumps(jobs, indent=2), encoding="utf-8")


def load_pending_batch_job(domain: str) -> Optional[str]:
    """Retourne un batch_id en attente pour ce domaine, ou None."""
    if not BATCH_JOBS_FILE.exists():
        return None
    try:
        jobs = json.loads(BATCH_JOBS_FILE.read_text(encoding="utf-8"))
        return jobs.get(domain, {}).get("batch_id")
    except (json.JSONDecodeError, KeyError):
        return None


def clear_batch_job(domain: str) -> None:
    """Supprime le batch_id après traitement réussi."""
    if not BATCH_JOBS_FILE.exists():
        return
    try:
        jobs = json.loads(BATCH_JOBS_FILE.read_text(encoding="utf-8"))
        jobs.pop(domain, None)
        BATCH_JOBS_FILE.write_text(json.dumps(jobs, indent=2), encoding="utf-8")
    except (json.JSONDecodeError, OSError):
        pass


# ── Anthropic Batch API ───────────────────────────────────────────────────────

def submit_batch(papers: list, client: anthropic.Anthropic) -> str:
    """Soumet tous les papers à l'Anthropic Batch API. Retourne le batch_id."""
    requests = []
    for paper in papers:
        paper_id = paper.get("paper_id") or paper.get("arxiv_id", "unknown")
        user_content = USER_PROMPT_TEMPLATE.format(
            title=paper.get("title", ""),
            domain=paper.get("domain", ""),
            paper_id=paper_id,
            source_url=paper.get("source_url", ""),
            content=paper["content"][:3000],
        )
        requests.append({
            "custom_id": str(paper["path"]),
            "params": {
                "model": MODEL,
                "max_tokens": MAX_TOKENS_CONCEPTS,
                "system": [
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                "messages": [{"role": "user", "content": user_content}],
            },
        })
    batch = client.messages.batches.create(requests=requests)
    return batch.id


def wait_for_batch(batch_id: str, client: anthropic.Anthropic,
                   poll_interval: int = 15,
                   max_wait_seconds: int = 86400) -> None:
    """Poll until the batch is complete. Raises TimeoutError after max_wait_seconds."""
    print(f"  [INFO] Batch {batch_id} soumis, polling…", file=sys.stderr)
    elapsed = 0
    while True:
        status = client.messages.batches.retrieve(batch_id)
        if status.processing_status == "ended":
            return
        counts = status.request_counts
        print(
            f"  [INFO] Batch {batch_id} — processing: {counts.processing} "
            f"succeeded: {counts.succeeded} errored: {counts.errored} "
            f"[{elapsed}s elapsed]",
            file=sys.stderr,
        )
        if elapsed >= max_wait_seconds:
            raise TimeoutError(
                f"Batch {batch_id} did not complete within {max_wait_seconds}s"
            )
        time.sleep(poll_interval)
        elapsed += poll_interval


def _build_concepts_summary(concepts: list[dict]) -> str:
    lines = []
    for c in concepts:
        lines.append(f"[{c.get('tier','?')}] {c.get('concept_title','')}: {c.get('essence','')[:120]}")
    return "\n".join(lines)




# ── Domain processing ─────────────────────────────────────────────────────────

def process_domain(
    domain: str,
    week_num: int,
    today: str,
    min_tier: str,
    dry_run: bool,
) -> dict:
    """Process one domain via Anthropic Batch API. Returns metrics dict."""
    print(f"\n── Domain: {domain} ──────────────────────────────────────────")

    papers = load_papers(domain)
    if not papers:
        print(f"  No papers found — skipping.")
        return {"domain": domain, "skipped": True}

    print(f"  Found {len(papers)} paper(s)")

    if dry_run:
        print(f"  [dry-run] Would submit {len(papers)} paper(s) to Anthropic Batch API")
        for p in papers:
            pid = p.get("paper_id") or p.get("arxiv_id", "unknown")
            print(f"    - {pid}: {p['title'][:60]}")
        return {"domain": domain, "dry_run": True, "papers": len(papers)}

    client = anthropic.Anthropic()
    min_tier_val = TIER_ORDER.get(min_tier, 1)

    # ── Recovery : si un batch est déjà en cours pour ce domaine ────────────
    batch_id = load_pending_batch_job(domain)
    if batch_id:
        print(f"  [INFO] Resuming existing batch {batch_id}")
    else:
        # Enrichir les papers avec paper_id depuis frontmatter
        for p in papers:
            meta, _ = parse_frontmatter(p["content"])
            p["paper_id"] = meta.get("paper_id", p.get("arxiv_id", ""))

        batch_id = submit_batch(papers, client)
        save_batch_job(domain, batch_id)
        print(f"  [INFO] Batch soumis : {batch_id}")

    # ── Attendre la fin du batch ─────────────────────────────────────────────
    wait_for_batch(batch_id, client)

    # ── Construire index papers par path pour lookup dans les résultats ──────
    papers_by_path = {str(p["path"]): p for p in papers}

    # ── Traiter les résultats ────────────────────────────────────────────────
    all_concepts: list[dict] = []
    errors: list[str] = []

    for result in client.messages.batches.results(batch_id):
        if result.result.type != "succeeded":
            errors.append(f"{result.custom_id}: {result.result.type}")
            print(f"  [WARN] {result.custom_id}: {result.result.type}", file=sys.stderr)
            continue

        content_blocks = result.result.message.content
        if not content_blocks:
            errors.append(f"{result.custom_id}: empty response content")
            continue
        raw_text = content_blocks[0].text
        concepts = parse_concepts_from_text(raw_text)

        paper = papers_by_path.get(result.custom_id, {})
        paper_id = paper.get("paper_id", paper.get("arxiv_id", ""))
        source_url = paper.get("source_url", "")

        filtered = [c for c in concepts
                    if TIER_ORDER.get(c.get("tier", "B"), 1) >= min_tier_val]

        for c in filtered:
            c.setdefault("paper_id", paper_id)
            c.setdefault("source_url", source_url)
        all_concepts.extend(filtered)

    # ── Écrire les notes atomiques ───────────────────────────────────────────
    concepts_by_paper: dict = defaultdict(list)
    for c in all_concepts:
        concepts_by_paper[c.get("paper_id", "unknown")].append(c)

    written_paths: list[Path] = []
    for pid, concepts in concepts_by_paper.items():
        for n, concept in enumerate(concepts, 1):
            path = write_concept_note(concept, domain, week_num, today, index=n)
            written_paths.append(path)
            print(f"  -> {path.name}")

    # ── Générer le digest domaine ────────────────────────────────────────────
    digest_path = None
    if all_concepts:
        digest_response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS_DIGEST,
            system=[{"type": "text", "text": "Tu crées des notes de littérature synthétiques pour un vault Obsidian. Réponds en markdown direct, pas de JSON."}],
            messages=[{
                "role": "user",
                "content": DIGEST_PROMPT.format(
                    week_num=week_num,
                    domain=domain,
                    paper_titles="\n".join(f"- {p['title']}" for p in papers),
                    concepts_summary=_build_concepts_summary(all_concepts),
                ),
            }],
        )
        digest_text = digest_response.content[0].text
        digest_path = write_digest(
            domain, week_num, digest_text,
            [p["title"] for p in papers], papers, today
        )
        print(f"  Digest -> {digest_path.name}")

    # ── Déplacer les papers traités ──────────────────────────────────────────
    processed_dir = PAPERS_DIR / domain / "_processed"
    processed_dir.mkdir(exist_ok=True)
    for paper in papers:
        dest = processed_dir / paper["path"].name
        try:
            paper["path"].rename(dest)
        except OSError as exc:
            print(f"  [WARN] Could not move {paper['path'].name}: {exc}", file=sys.stderr)

    # ── Cleanup batch job ────────────────────────────────────────────────────
    clear_batch_job(domain)

    tier_dist: dict[str, int] = {"S": 0, "A": 0, "B": 0}
    for c in all_concepts:
        t = c.get("tier", "B")
        tier_dist[t] = tier_dist.get(t, 0) + 1

    return {
        "domain": domain,
        "papers_processed": len(papers),
        "concepts_extracted": len(all_concepts),
        "tier_distribution": tier_dist,
        "digest_created": digest_path is not None,
        "errors": errors,
    }


# ── Metrics writer ────────────────────────────────────────────────────────────

def write_metrics(metrics_list: list[dict], week_num: int, today: str) -> None:
    LOGS_DIR.mkdir(exist_ok=True)
    out_path = LOGS_DIR / "synthesizer-last-run.json"

    domains_processed = [m["domain"] for m in metrics_list if not m.get("skipped") and not m.get("dry_run")]
    papers_total = sum(m.get("papers_processed", 0) for m in metrics_list)
    concepts_total = sum(m.get("concepts_extracted", 0) for m in metrics_list)
    digests_total = sum(1 for m in metrics_list if m.get("digest_created"))

    tier_dist: dict[str, int] = {"S": 0, "A": 0, "B": 0}
    for m in metrics_list:
        for tier, count in m.get("tier_distribution", {}).items():
            tier_dist[tier] = tier_dist.get(tier, 0) + count

    all_errors = []
    for m in metrics_list:
        all_errors.extend(m.get("errors", []))

    # Estimate tokens (Claude Haiku Batch ~$0.40/MTok input, $2/MTok output)
    estimated_tokens = concepts_total * MAX_TOKENS_CONCEPTS + digests_total * MAX_TOKENS_DIGEST

    payload = {
        "run_date": today,
        "week": week_num,
        "model": MODEL,
        "api": "anthropic-claude-haiku-batch",
        "domains_processed": domains_processed,
        "papers_processed": papers_total,
        "concepts_extracted": concepts_total,
        "tier_distribution": tier_dist,
        "digests_created": digests_total,
        "estimated_tokens": estimated_tokens,
        "estimated_cost_usd": 0.0,
        "errors": all_errors,
    }

    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nMetrics -> {out_path}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Paper synthesizer — Claude Haiku Batch")
    parser.add_argument("--domain", choices=DOMAINS, default=None,
                        help="Domaine spécifique (défaut : tous)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Afficher les papers sans appeler l'API")
    parser.add_argument("--week", type=int, default=None,
                        help="Numéro de semaine ISO (défaut : semaine courante)")
    parser.add_argument("--min-tier", choices=["S", "A", "B"], default="B",
                        dest="min_tier",
                        help="Tier minimum à écrire (défaut : B)")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY") and not args.dry_run:
        print("[ERROR] ANTHROPIC_API_KEY non définie. Export requis.", file=sys.stderr)
        sys.exit(1)

    today = date.today().isoformat()
    week_num = args.week or date.today().isocalendar()[1]
    domains_to_run = [args.domain] if args.domain else DOMAINS

    metrics_list = []
    for domain in domains_to_run:
        metrics = process_domain(domain, week_num, today, args.min_tier, args.dry_run)
        metrics_list.append(metrics)

    if not args.dry_run:
        write_metrics(metrics_list, week_num, today)
        print(f"\n[INFO] Synthesis terminée — résultats dans {CONCEPTS_DIR}")


if __name__ == "__main__":
    main()
