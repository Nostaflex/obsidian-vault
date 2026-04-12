#!/usr/bin/env python3
"""
corpus_collector.py — Collecte automatique de papers scientifiques
Domaines : AI, IoT, Cloud, E-commerce via arXiv + Semantic Scholar
Usage : python3 corpus_collector.py [--domain DOMAIN] [--since DAYS] [--max N]
         [--min-score FLOAT]

Nouveautés v2 :
- Scoring de pertinence composite (vault_relevance + citation_velocity + recency)
- Filtre tier C (score < 0.3 ignorés silencieusement)
- Déduplication robuste par arxiv_id normalisé (sans suffixe de version)
- Frontmatter enrichi (relevance_score, tier, citation_count, keywords)
- Logging détaillé : doublons, filtrés, distribution tier
"""

import argparse
import json
import math
import os
import re
import subprocess
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
VAULT = Path(os.environ.get("HOME", "~")) / "Documents/Obsidian/KnowledgeBase"
RAW_DIR = VAULT / "_inbox/raw/papers"
REBUILD_SCRIPT = VAULT / "corpus-rebuild.sh"
SEEN_IDS_FILE = VAULT / "_logs/seen-arxiv-ids.txt"
INDEX_FILE = VAULT / "_meta/INDEX.md"

DOMAINS = {
    "ai":        ["cs.AI", "cs.LG", "cs.CL", "cs.MA"],
    "iot":       ["cs.NI", "cs.SY", "eess.SP"],
    "cloud":     ["cs.DC", "cs.PF"],
    "ecommerce": ["cs.IR", "cs.HC"],
}
SS_QUERIES = {
    "ai":  "AI agents LLM 2025",
    "iot": "IoT edge computing 2025",
}

# Mots-clés de repli par domaine si INDEX.md est absent
DOMAIN_FALLBACK_KEYWORDS = {
    "ai":        ["ai", "llm", "agent", "transformer", "neural", "language model",
                  "reinforcement", "machine learning", "deep learning", "multimodal"],
    "iot":       ["iot", "edge", "sensor", "embedded", "mqtt", "wireless", "protocol",
                  "network", "real-time", "low-power"],
    "cloud":     ["cloud", "distributed", "kubernetes", "microservice", "serverless",
                  "container", "scalability", "fault tolerance", "latency"],
    "ecommerce": ["ecommerce", "recommender", "search", "ranking", "user interface",
                  "click", "conversion", "product", "retail", "recommendation"],
}

DEFAULT_MAX = 5       # réduit de 10 à 5 pour limiter le Collector's Fallacy
DEFAULT_MIN_SCORE = 0.3


# ── Déduplication arxiv_id ────────────────────────────────────────────────────

def normalize_arxiv_id(arxiv_id: str) -> str:
    """Retire le suffixe de version : '2403.12345v2' -> '2403.12345'."""
    return re.sub(r'v\d+$', '', arxiv_id.strip())


def load_seen_ids() -> set:
    """Charge les arxiv_ids déjà vus depuis _logs/seen-arxiv-ids.txt."""
    if not SEEN_IDS_FILE.exists():
        return set()
    lines = SEEN_IDS_FILE.read_text(encoding="utf-8").splitlines()
    return {line.strip() for line in lines if line.strip()}


def save_seen_ids(seen: set) -> None:
    """Persiste l'ensemble des arxiv_ids vus (trié pour lisibilité)."""
    SEEN_IDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEEN_IDS_FILE.write_text("\n".join(sorted(seen)) + "\n", encoding="utf-8")


# ── Tags vault ────────────────────────────────────────────────────────────────

def load_vault_tags() -> list:
    """
    Extrait les tags actifs du vault depuis _meta/INDEX.md.
    Retourne une liste de mots-clés en minuscules (sans le '#').
    Si INDEX.md est absent, retourne une liste vide (fallback géré en aval).
    """
    if not INDEX_FILE.exists():
        return []
    text = INDEX_FILE.read_text(encoding="utf-8")
    # Trouver tous les tokens #tag dans le fichier
    tags = re.findall(r'#([\w\-]+)', text)
    # Normaliser et dédupliquer
    return list({t.lower() for t in tags})


# ── Scoring ───────────────────────────────────────────────────────────────────

def compute_relevance_score(paper: dict, vault_tags: list, domain: str) -> float:
    """
    Score composite 0.0-1.0 pour un paper.

    Composantes :
    - vault_relevance (0.4) : mots-clés du paper présents dans les tags actifs du vault
    - citation_velocity (0.3) : citationCount normalisé (log scale, max 1000)
    - recency (0.3) : 1.0 si < 7 jours, 0.7 si < 30 jours, 0.4 si < 90 jours, 0.1 sinon

    Si vault_tags est vide → vault_relevance = 0.5 (fallback par domaine).
    """
    # ── 1. Vault relevance ──────────────────────────────────────────────────
    text_to_search = (
        (paper.get("title") or "") + " " + (paper.get("abstract") or "")
    ).lower()

    if vault_tags:
        # Compter combien de tags vault apparaissent dans le texte du paper
        matches = sum(1 for tag in vault_tags if tag in text_to_search)
        vault_relevance = min(1.0, matches / max(len(vault_tags) * 0.1, 1))
    else:
        # Fallback : utiliser les mots-clés hardcodés par domaine
        fallback_kw = DOMAIN_FALLBACK_KEYWORDS.get(domain, [])
        if fallback_kw:
            matches = sum(1 for kw in fallback_kw if kw in text_to_search)
            vault_relevance = min(1.0, matches / max(len(fallback_kw) * 0.2, 1))
        else:
            vault_relevance = 0.5  # neutre si aucun indice disponible

    # ── 2. Citation velocity ────────────────────────────────────────────────
    citation_count = paper.get("citation_count") or 0
    if citation_count > 0:
        citation_velocity = min(1.0, math.log(citation_count + 1) / math.log(1001))
    else:
        citation_velocity = 0.0

    # ── 3. Recency ──────────────────────────────────────────────────────────
    date_str = paper.get("date", "")
    try:
        # Accepter YYYY-MM-DD ou YYYY
        if len(date_str) >= 10:
            pub_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
        elif len(date_str) == 4:
            pub_date = datetime(int(date_str), 1, 1)
        else:
            pub_date = None
    except ValueError:
        pub_date = None

    if pub_date:
        age_days = (datetime.utcnow() - pub_date).days
        if age_days < 7:
            recency = 1.0
        elif age_days < 30:
            recency = 0.7
        elif age_days < 90:
            recency = 0.4
        else:
            recency = 0.1
    else:
        recency = 0.1  # date inconnue → pénalisé

    # ── Score final ─────────────────────────────────────────────────────────
    score = (
        0.4 * vault_relevance +
        0.3 * citation_velocity +
        0.3 * recency
    )
    return round(score, 4)


def score_to_tier(score: float) -> str:
    """Convertit un score en tier : S / A / B / C."""
    if score > 0.8:
        return "S"
    elif score > 0.5:
        return "A"
    elif score > 0.3:
        return "B"
    else:
        return "C"


def extract_keywords(paper: dict, max_kw: int = 8) -> list:
    """
    Extrait des mots-clés simples depuis le titre + abstract.
    Approche légère : tokens longs et fréquents, sans dépendance externe.
    """
    text = (
        (paper.get("title") or "") + " " + (paper.get("abstract") or "")
    ).lower()
    # Supprimer la ponctuation
    text = re.sub(r'[^a-z0-9\s\-]', ' ', text)
    tokens = text.split()
    # Filtrer : longueur >= 4, exclure stop-words courants
    stop = {
        "with", "that", "this", "from", "have", "been", "they", "their",
        "which", "also", "more", "into", "than", "when", "where", "show",
        "such", "each", "over", "most", "both", "after", "using", "used",
        "based", "data", "model", "models", "results", "paper", "propose",
        "approach", "method", "task", "tasks", "learning", "training",
    }
    freq: dict = {}
    for t in tokens:
        if len(t) >= 4 and t not in stop:
            freq[t] = freq.get(t, 0) + 1
    # Trier par fréquence décroissante
    sorted_kw = sorted(freq, key=lambda k: freq[k], reverse=True)
    return sorted_kw[:max_kw]


# ── Helpers réseau ────────────────────────────────────────────────────────────

def arxiv_fetch(categories, since_days, max_results):
    """Interroge l'API arXiv et retourne une liste de dicts paper."""
    cat_query = " OR ".join(f"cat:{c}" for c in categories)
    since_date = (datetime.utcnow() - timedelta(days=since_days)).strftime("%Y%m%d")
    query = f"({cat_query}) AND submittedDate:[{since_date}0000 TO 99991231235959]"
    params = urllib.parse.urlencode({
        "search_query": query,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    })
    url = f"https://export.arxiv.org/api/query?{params}"
    with urllib.request.urlopen(url, timeout=30) as r:
        data = r.read()
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(data)
    papers = []
    for entry in root.findall("atom:entry", ns):
        arxiv_url = entry.findtext("atom:id", "", ns).strip()
        arxiv_id = arxiv_url.split("/abs/")[-1] if "/abs/" in arxiv_url else ""
        papers.append({
            "title":          entry.findtext("atom:title", "", ns).strip().replace("\n", " "),
            "abstract":       entry.findtext("atom:summary", "", ns).strip().replace("\n", " "),
            "source_url":     arxiv_url,
            "arxiv_id":       arxiv_id,
            "authors":        [a.findtext("atom:name", "", ns) for a in entry.findall("atom:author", ns)],
            "date":           entry.findtext("atom:published", "", ns)[:10],
            "source":         "arXiv",
            "citation_count": 0,  # arXiv ne fournit pas le citation count
        })
    return papers


def semantic_scholar_fetch(query, max_results=5):
    """Interroge Semantic Scholar (gratuit, sans clé API)."""
    params = urllib.parse.urlencode({
        "query": query,
        "limit": max_results,
        "fields": "title,abstract,year,authors,externalIds,url,citationCount",
    })
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "corpus-collector/2.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
        papers = []
        for p in data.get("data", []):
            ext = p.get("externalIds") or {}
            arxiv_id = ext.get("ArXiv", "")
            source_url = p.get("url") or (f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else "")
            papers.append({
                "title":          p.get("title", ""),
                "abstract":       p.get("abstract", "") or "",
                "source_url":     source_url,
                "arxiv_id":       arxiv_id,
                "authors":        [a["name"] for a in p.get("authors", [])],
                "date":           str(p.get("year", "")),
                "source":         "Semantic Scholar",
                "citation_count": p.get("citationCount") or 0,
            })
        return papers
    except Exception as e:
        print(f"  [warn] Semantic Scholar: {e}")
        return []


# ── Formatage markdown ────────────────────────────────────────────────────────

def format_paper_as_markdown(paper: dict, domain: str) -> str:
    """
    Convertit un dict paper en fichier markdown avec frontmatter YAML enrichi.
    Inclut : relevance_score, tier, citation_count, keywords, arxiv_id_normalized,
             collected (date de collecte).
    """
    # Auteurs : liste YAML (5 max)
    authors_list = paper.get("authors", [])[:5]
    authors_yaml_lines = "\n".join(f'  - "{a}"' for a in authors_list)
    authors_yaml = f"\n{authors_yaml_lines}" if authors_yaml_lines else " []"

    # Keywords
    kw_list = paper.get("keywords", [])
    kw_yaml_lines = "\n".join(f'  - "{k}"' for k in kw_list)
    kw_yaml = f"\n{kw_yaml_lines}" if kw_yaml_lines else " []"

    abstract = paper["abstract"][:1000] if paper["abstract"] else "(abstract non disponible)"
    authors_str = ", ".join(authors_list[:3])
    if len(paper.get("authors", [])) > 3:
        authors_str += " et al."
    source_line = f"{paper['source']} · {paper['date']}"
    url_comment = f"<!-- source-url: {paper['source_url']} -->" if paper.get("source_url") else ""

    arxiv_id = paper.get("arxiv_id", "")
    arxiv_id_norm = normalize_arxiv_id(arxiv_id) if arxiv_id else ""
    collected = datetime.utcnow().strftime("%Y-%m-%d")

    return f"""---
type: paper
domain: {domain}
arxiv_id: "{arxiv_id}"
arxiv_id_normalized: "{arxiv_id_norm}"
authors:{authors_yaml}
date: "{paper['date']}"
source: {paper['source']}
source_url: "{paper.get('source_url', '')}"
relevance_score: {paper.get('relevance_score', 0.0)}
tier: {paper.get('tier', 'C')}
citation_count: {paper.get('citation_count', 0)}
keywords:{kw_yaml}
collected: "{collected}"
---

# {paper["title"]}

**Abstract :** {abstract}

**Auteurs :** {authors_str}
**Source :** {source_line}

{url_comment}
"""


# ── Sauvegarde ────────────────────────────────────────────────────────────────

def save_papers(papers: list, domain: str, seen_ids: set,
                vault_tags: list, min_score: float,
                raw_dir: Path = None) -> dict:
    """
    Filtre, score et sauvegarde les papers.

    Retourne un dict de stats :
      saved, duplicates, tier_c_filtered, scores, tier_counts
    """
    if raw_dir is None:
        raw_dir = RAW_DIR
    out_dir = Path(raw_dir) / domain
    out_dir.mkdir(parents=True, exist_ok=True)

    stats = {
        "saved": 0,
        "duplicates": 0,
        "tier_c_filtered": 0,
        "scores": [],
        "tier_counts": {"S": 0, "A": 0, "B": 0, "C": 0},
    }

    for p in papers:
        if not p.get("title"):
            continue

        # ── Déduplication par arxiv_id normalisé ────────────────────────────
        arxiv_id_raw = p.get("arxiv_id", "")
        arxiv_id_norm = normalize_arxiv_id(arxiv_id_raw) if arxiv_id_raw else ""
        if arxiv_id_norm and arxiv_id_norm in seen_ids:
            stats["duplicates"] += 1
            continue

        # ── Scoring ─────────────────────────────────────────────────────────
        score = compute_relevance_score(p, vault_tags, domain)
        tier = score_to_tier(score)
        stats["tier_counts"][tier] += 1

        if score < min_score:
            stats["tier_c_filtered"] += 1
            continue  # tier C silencieusement ignoré

        # ── Enrichissement du dict paper ────────────────────────────────────
        p["relevance_score"] = score
        p["tier"] = tier
        p["keywords"] = extract_keywords(p)

        # ── Sauvegarde fichier ───────────────────────────────────────────────
        slug = p["title"][:60].lower()
        slug = "".join(c if c.isalnum() else "_" for c in slug).strip("_")
        fname = out_dir / f"{p['date']}_{slug}.md"
        if not fname.exists():
            fname.write_text(format_paper_as_markdown(p, domain), encoding="utf-8")
            stats["saved"] += 1
            stats["scores"].append(score)

            # Marquer l'id comme vu
            if arxiv_id_norm:
                seen_ids.add(arxiv_id_norm)

    return stats


# ── Main ──────────────────────────────────────────────────────────────────────

def run(domain_filter, since_days, max_per_domain, min_score):
    targets = {domain_filter: DOMAINS[domain_filter]} if domain_filter else DOMAINS
    total_saved = 0

    # Charger état initial : ids déjà vus + tags vault
    seen_ids = load_seen_ids()
    vault_tags = load_vault_tags()

    if vault_tags:
        print(f"[INFO] {len(vault_tags)} tags vault chargés depuis INDEX.md")
    else:
        print("[INFO] INDEX.md absent ou sans tags — fallback mots-clés par domaine")

    for domain, cats in targets.items():
        print(f"\n[INFO] Domain {domain}: collecte arXiv ({', '.join(cats)}) …")
        papers = arxiv_fetch(cats, since_days, max_per_domain)

        stats = save_papers(papers, domain, seen_ids, vault_tags, min_score)
        avg = (sum(stats["scores"]) / len(stats["scores"])) if stats["scores"] else 0.0
        tc = stats["tier_counts"]
        print(
            f"[INFO] Domain {domain}: {len(papers)} fetched, "
            f"{stats['duplicates']} duplicates, "
            f"{stats['tier_c_filtered']} tier-C filtered "
            f"→ {stats['saved']} saved "
            f"(avg score: {avg:.2f}, "
            f"S:{tc['S']} A:{tc['A']} B:{tc['B']})"
        )
        total_saved += stats["saved"]
        time.sleep(1)

        if domain in SS_QUERIES:
            print(f"[INFO] Domain {domain}: Semantic Scholar '{SS_QUERIES[domain]}' …")
            ss_papers = semantic_scholar_fetch(SS_QUERIES[domain], max_results=max_per_domain)
            ss_stats = save_papers(ss_papers, domain, seen_ids, vault_tags, min_score)
            ss_avg = (sum(ss_stats["scores"]) / len(ss_stats["scores"])) if ss_stats["scores"] else 0.0
            stc = ss_stats["tier_counts"]
            print(
                f"[INFO] Domain {domain} (SS): {len(ss_papers)} fetched, "
                f"{ss_stats['duplicates']} duplicates, "
                f"{ss_stats['tier_c_filtered']} tier-C filtered "
                f"→ {ss_stats['saved']} saved "
                f"(avg score: {ss_avg:.2f}, "
                f"S:{stc['S']} A:{stc['A']} B:{stc['B']})"
            )
            total_saved += ss_stats["saved"]
            time.sleep(1)

    # Persister les ids vus (incluant ceux ajoutés cette session)
    save_seen_ids(seen_ids)

    print(f"\n[INFO] Collecte terminée — {total_saved} nouveaux fichiers dans {RAW_DIR}")

    if REBUILD_SCRIPT.exists() and total_saved > 0:
        print("[INFO] Rebuild corpus claude-mem …")
        subprocess.run(["bash", str(REBUILD_SCRIPT)], check=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collecte de papers multi-domaines")
    parser.add_argument("--domain", choices=list(DOMAINS.keys()), default=None,
                        help="Domaine spécifique (défaut : tous)")
    parser.add_argument("--since", type=int, default=30,
                        help="Jours en arrière (défaut : 30)")
    parser.add_argument("--max", type=int, default=DEFAULT_MAX,
                        help=f"Papers max par domaine (défaut : {DEFAULT_MAX})")
    parser.add_argument("--min-score", type=float, default=DEFAULT_MIN_SCORE,
                        dest="min_score",
                        help=f"Score minimum pour sauvegarder un paper (défaut : {DEFAULT_MIN_SCORE})")
    args = parser.parse_args()
    run(args.domain, args.since, args.max, args.min_score)
