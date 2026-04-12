#!/usr/bin/env python3
"""
paper_synthesizer.py — Weekly paper synthesis pipeline
Runs after corpus_collector.py (Saturday/Sunday)
Uses Google Gemini 2.0 Flash (free tier) to extract atomic concepts from scientific papers.

Requirements:
  pip install google-generativeai

Environment:
  GOOGLE_API_KEY — Get free at https://aistudio.google.com/apikey

Free tier limits: 15 RPM, 1M TPM, 1500 RPD
Rate limiting: 4s delay between calls (well within limits)

Usage:
  python3 paper_synthesizer.py [--domain DOMAIN] [--dry-run] [--week N]
  python3 paper_synthesizer.py --domain ai --dry-run
  python3 paper_synthesizer.py --week 16 --min-tier A
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import date, datetime
from pathlib import Path

from google import genai
from google.genai import types as genai_types

# ── Constants ─────────────────────────────────────────────────────────────────

VAULT_ROOT = Path(__file__).parent
PAPERS_DIR = VAULT_ROOT / "_inbox" / "raw" / "papers"
CONCEPTS_DIR = VAULT_ROOT / "_inbox" / "raw" / "concepts"
RESEARCH_DIR = VAULT_ROOT / "universal" / "research"
LOGS_DIR = VAULT_ROOT / "_logs"

DOMAINS = ["ai", "iot", "cloud", "ecommerce"]

TIER_ORDER = {"S": 3, "A": 2, "B": 1}

MODEL = "gemini-2.0-flash"
MAX_TOKENS_CONCEPTS = 1024
MAX_TOKENS_DIGEST = 1500
GEMINI_RATE_LIMIT_DELAY = 4.0  # secondes entre appels (15 RPM max)

# Gemini model instance (configured in main after API key check)
model = None  # genai.Client, set in main()

# ── Prompts ───────────────────────────────────────────────────────────────────

CONCEPT_EXTRACTION_PROMPT = """Tu es un extracteur de concepts scientifiques pour un second brain Obsidian.

Paper à analyser :
{paper_content}

Domaine : {domain}
Projets actifs : gpparts (e-commerce Next.js), second-brain (PKM automatisé)

## Tâche

Extraire les concepts clés de ce paper qui méritent une note atomique.

Pour CHAQUE concept identifié, produis un bloc JSON séparé :
```json
{{
  "concept_title": "Phrase affirmative testable — le titre de la note",
  "tier": "S|A|B",
  "tier_reason": "Pourquoi ce tier (lien avec les projets actifs ou valeur générale)",
  "essence": "2-3 lignes reformulées dans tes propres mots — JAMAIS copié de l'abstract",
  "detail": "Explication complète reformulée",
  "tags": ["tag1", "tag2"],
  "simple_explanation": "Explique en 15 mots max comme à un enfant de 12 ans",
  "arxiv_id": "{arxiv_id}",
  "source_url": "{source_url}"
}}
```

Règles strictes :
- `concept_title` DOIT être une phrase affirmative (peut être vraie ou fausse). Exemple: "Le federated learning réduit les coûts de transmission de 60% sur edge IoT" pas "Federated learning"
- `essence` : reformule complètement — si tu ne peux pas expliquer simplement (simple_explanation), le concept est mal scopé
- Tier S : directement applicable à gpparts ou second-brain
- Tier A : concept solide à valeur future
- Tier B : référence intéressante, 1 phrase suffit
- Ignorer les contributions trop théoriques sans application pratique
- Minimum 1 concept, maximum 4 concepts par paper

Produis UNIQUEMENT les blocs JSON, séparés par des lignes vides."""

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

def write_concept_note(concept: dict, domain: str, week_num: int, today: str) -> Path:
    """Write a pre-note atomic file to _inbox/raw/concepts/. Returns the path."""
    CONCEPTS_DIR.mkdir(parents=True, exist_ok=True)

    slug = slugify(concept.get("concept_title", "untitled"))
    out_path = CONCEPTS_DIR / f"draft-{slug}.md"

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


# ── Gemini API helpers ────────────────────────────────────────────────────────

def _build_concepts_summary(concepts: list[dict]) -> str:
    lines = []
    for c in concepts:
        lines.append(f"[{c.get('tier','?')}] {c.get('concept_title','')}: {c.get('essence','')[:120]}")
    return "\n".join(lines)


def call_gemini(prompt: str, max_output_tokens: int = MAX_TOKENS_CONCEPTS,
                max_retries: int = 3) -> str:
    """Appel Gemini avec retry exponentiel en cas d'erreur rate limit."""
    for attempt in range(max_retries):
        try:
            response = model.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    max_output_tokens=max_output_tokens,
                    temperature=0.1,
                )
            )
            return response.text
        except Exception as e:
            print(f"[DEBUG] Attempt {attempt+1} error: {type(e).__name__}: {e}", file=sys.stderr)
            if "429" in str(e) or "quota" in str(e).lower() or "rate" in str(e).lower():
                wait = GEMINI_RATE_LIMIT_DELAY * (2 ** attempt)
                print(f"[WARN] Rate limit hit, waiting {wait:.0f}s…", file=sys.stderr)
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f"Failed after {max_retries} retries")


# ── Domain processing ─────────────────────────────────────────────────────────

def process_domain(
    domain: str,
    week_num: int,
    today: str,
    min_tier: str,
    dry_run: bool,
) -> dict:
    """Process one domain end-to-end sequentially. Returns metrics dict."""
    print(f"\n── Domain: {domain} ──────────────────────────────────────────")

    papers = load_papers(domain)
    if not papers:
        print(f"  No papers found — skipping.")
        return {"domain": domain, "skipped": True}

    print(f"  Found {len(papers)} paper(s)")

    if dry_run:
        print(f"  [dry-run] Would process {len(papers)} paper(s) sequentially with Gemini:")
        for i, paper in enumerate(papers):
            prompt_preview = CONCEPT_EXTRACTION_PROMPT.format(
                paper_content=paper["content"],
                domain=domain,
                arxiv_id=paper["arxiv_id"],
                source_url=paper["source_url"],
            )[:120].replace("\n", " ")
            print(f"    [paper_{i}] {prompt_preview}…")
        return {"domain": domain, "dry_run": True, "papers": len(papers)}

    # Process papers sequentially with rate limiting
    min_tier_val = TIER_ORDER.get(min_tier, 1)
    all_concepts: list[dict] = []

    for i, paper in enumerate(papers):
        print(f"  [INFO] Processing paper {i+1}/{len(papers)}: {paper['title'][:60]}")

        prompt = CONCEPT_EXTRACTION_PROMPT.format(
            paper_content=paper["content"],
            domain=domain,
            arxiv_id=paper["arxiv_id"],
            source_url=paper["source_url"],
        )

        raw_text = call_gemini(prompt, max_output_tokens=MAX_TOKENS_CONCEPTS)
        concepts = parse_concepts_from_text(raw_text)

        if not concepts:
            print(f"  [WARN] No valid JSON concepts parsed for paper_{i}")
        else:
            # Filter by min tier
            filtered = [c for c in concepts if TIER_ORDER.get(c.get("tier", "B"), 1) >= min_tier_val]
            if not filtered:
                print(f"  Skipped {paper['title'][:50]}: all concepts below tier {min_tier}")
            else:
                # Inject paper metadata into each concept (fallback if LLM left blanks)
                for c in filtered:
                    c.setdefault("source_url", paper["source_url"])
                    c.setdefault("arxiv_id", paper["arxiv_id"])
                all_concepts.extend(filtered)
                print(f"  paper_{i}: {len(filtered)} concept(s) extracted")

        # Rate limiting — skip delay after last paper
        if i < len(papers) - 1:
            time.sleep(GEMINI_RATE_LIMIT_DELAY)

    # Write concept pre-notes
    written_paths: list[Path] = []
    for concept in all_concepts:
        path = write_concept_note(concept, domain, week_num, today)
        written_paths.append(path)
        print(f"  -> {path.name}")

    # Generate digest with actual concepts
    digest_path = None
    print(f"  [INFO] Generating digest for {domain}…")
    paper_titles_str = "\n".join(f"- {p['title']}" for p in papers)
    digest_prompt = DIGEST_PROMPT.format(
        week_num=week_num,
        domain=domain,
        paper_titles=paper_titles_str,
        concepts_summary=_build_concepts_summary(all_concepts) if all_concepts
            else "Aucun concept extrait pour ce domaine cette semaine.",
    )
    digest_text = call_gemini(digest_prompt, max_output_tokens=MAX_TOKENS_DIGEST)

    if digest_text:
        digest_path = write_digest(
            domain, week_num, digest_text,
            [p["title"] for p in papers], papers, today
        )
        print(f"  Digest -> {digest_path.name}")

    # Move processed papers to _processed/
    processed_dir = PAPERS_DIR / domain / "_processed"
    processed_dir.mkdir(exist_ok=True)
    for paper in papers:
        dest = processed_dir / paper["path"].name
        try:
            paper["path"].rename(dest)
        except OSError as exc:
            print(f"  [WARN] Could not move {paper['path'].name}: {exc}", file=sys.stderr)

    # Tier distribution
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

    # Rough token estimate (for informational purposes only — Gemini free tier has no cost)
    estimated_tokens = concepts_total * MAX_TOKENS_CONCEPTS + digests_total * MAX_TOKENS_DIGEST

    payload = {
        "run_date": today,
        "week": week_num,
        "model": MODEL,
        "api": "google-gemini-free-tier",
        "domains_processed": domains_processed,
        "papers_processed": papers_total,
        "concepts_extracted": concepts_total,
        "tier_distribution": tier_dist,
        "digests_created": digests_total,
        "estimated_tokens": estimated_tokens,
        "estimated_cost_usd": 0.0,
    }

    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nMetrics -> {out_path}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Synthesize scientific papers into atomic Obsidian pre-notes.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--domain",
        choices=DOMAINS,
        help="Process only this domain (ai|iot|cloud|ecommerce)",
    )
    parser.add_argument(
        "--week",
        type=int,
        default=None,
        help="ISO week number to tag outputs (default: current week)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print prompts without calling the API",
    )
    parser.add_argument(
        "--min-tier",
        choices=["B", "A", "S"],
        default="B",
        help="Minimum tier to include in output (default: B = all tiers)",
    )
    return parser.parse_args()


def main() -> None:
    global model
    args = parse_args()

    # Validate API key early
    if not args.dry_run:
        google_api_key = os.environ.get("GOOGLE_API_KEY", "")
        if not google_api_key:
            print(
                "Error: GOOGLE_API_KEY not set\n"
                "Get a free key at: https://aistudio.google.com/apikey",
                file=sys.stderr,
            )
            sys.exit(1)
        model = genai.Client(api_key=google_api_key)

    today = date.today().isoformat()
    week_num = args.week if args.week is not None else date.today().isocalendar()[1]
    domains_to_run = [args.domain] if args.domain else DOMAINS

    print(f"paper_synthesizer.py — W{week_num} {today}")
    print(f"Domains : {', '.join(domains_to_run)}")
    print(f"Model   : {MODEL} (Google Gemini free tier)")
    print(f"Min tier: {args.min_tier} | dry-run: {args.dry_run}")

    all_metrics: list[dict] = []
    for domain in domains_to_run:
        metrics = process_domain(
            domain=domain,
            week_num=week_num,
            today=today,
            min_tier=args.min_tier,
            dry_run=args.dry_run,
        )
        all_metrics.append(metrics)

    if not args.dry_run:
        write_metrics(all_metrics, week_num, today)

    # Summary
    total_papers = sum(m.get("papers_processed", 0) for m in all_metrics)
    total_concepts = sum(m.get("concepts_extracted", 0) for m in all_metrics)
    print(f"\nDone. {total_papers} paper(s) processed, {total_concepts} concept note(s) written.")


if __name__ == "__main__":
    main()
