#!/usr/bin/env python3
"""
practitioner_collector.py — Collecte praicienne pour architecte solution cloud.
Sources : RSS blogs officiels + Hacker News Algolia API.
Domaines : gcp, firebase, cloud-native, architecture, devops, ai-engineering, security.
Usage : python3 practitioner_collector.py [--domain DOMAIN] [--since DAYS] [--max N]
                                           [--dry-run] [--force]
"""

import argparse
import hashlib
import http.client
import json
import math
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

VAULT = Path(os.environ.get("HOME", "~")) / "Documents/Obsidian/KnowledgeBase"
RAW_DIR = VAULT / "_inbox/raw/papers"
SEEN_IDS_FILE = VAULT / "_logs/seen-paper-ids.txt"

DEFAULT_MAX = 10
DEFAULT_MIN_SCORE = 0.3
DEFAULT_SINCE = 7
HN_MIN_POINTS = 50
FETCH_TIMEOUT = 10
PRAC_PREFIX = "prac-"

# ── Sources RSS ───────────────────────────────────────────────────────────────

DOMAINS_RSS = {
    "gcp": [
        "https://cloudblog.withgoogle.com/rss/",
        "https://cloud.google.com/blog/feed",
    ],
    "firebase": [
        "https://firebase.googleblog.com/feeds/posts/default",
    ],
    "cloud-native": [
        "https://www.cncf.io/feed/",
        "https://kubernetes.io/feed.xml",
    ],
    "architecture": [
        "https://martinfowler.com/feed.atom",
        "https://www.infoq.com/architecture-design/rss/",
    ],
    "devops": [
        "https://www.infoq.com/devops/rss/",
        "https://thenewstack.io/feed/",
    ],
    "ai-engineering": [
        "https://www.infoq.com/ai-ml-data-eng/rss/",
    ],
    "security": [
        "https://cloudblog.withgoogle.com/topics/threat-intelligence/rss/",
        "https://thenewstack.io/category/security/feed/",
    ],
}

DOMAIN_HN_KEYWORDS = {
    "gcp":            ["gcp", "google cloud", "cloud run", "bigquery", "vertex ai"],
    "firebase":       ["firebase", "firestore", "app check"],
    "cloud-native":   ["kubernetes", "k8s", "istio", "cncf", "platform engineering"],
    "architecture":   ["distributed systems", "event-driven", "ddd", "microservices"],
    "devops":         ["terraform", "gitops", "ci/cd", "pulumi", "iac"],
    "ai-engineering": ["llmops", "rag", "llm", "prompt engineering", "agents"],
    "security":       ["zero trust", "iam", "owasp", "cloud security"],
}

DOMAIN_FALLBACK_KEYWORDS = {
    "gcp":            ["gcp", "google cloud", "cloud run", "gke", "bigquery",
                       "vertex", "pubsub", "spanner", "cloud sql", "cloud functions"],
    "firebase":       ["firebase", "firestore", "realtime database", "app check",
                       "cloud functions", "firebase auth", "remote config"],
    "cloud-native":   ["kubernetes", "k8s", "helm", "istio", "cncf", "argo",
                       "platform engineering", "service mesh", "containerd"],
    "architecture":   ["distributed", "event-driven", "microservices", "ddd",
                       "saga", "cqrs", "eventual consistency", "hexagonal"],
    "devops":         ["terraform", "gitops", "ci/cd", "pulumi", "iac",
                       "github actions", "jenkins", "argocd", "flux"],
    "ai-engineering": ["llm", "rag", "prompt", "langchain", "llmops",
                       "embedding", "vector", "agent", "fine-tuning"],
    "security":       ["zero trust", "iam", "owasp", "soc2", "oauth",
                       "cloud security", "devsecops", "secret", "vault"],
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def score_to_tier(score: float) -> str:
    """Convertit un score 0.0-1.0 en tier S/A/B/C."""
    if score >= 0.7:
        return "S"
    if score >= 0.5:
        return "A"
    if score >= 0.3:
        return "B"
    return "C"


def score_article(title: str, summary: str, domain: str,
                  published_date: datetime) -> float:
    """
    Score de pertinence 0.0-1.0 pour un article praicien.

    Composantes :
    - keyword match titre (max 0.5) : chaque keyword +0.25
    - keyword match résumé (max 0.2) : chaque keyword +0.05
    - recency (max 0.3) : décroissance exponentielle exp(-0.1 * age_days)
    """
    keywords = DOMAIN_FALLBACK_KEYWORDS.get(domain, [])
    title_lower = title.lower()
    summary_lower = summary.lower()

    title_matches = sum(1 for kw in keywords if kw in title_lower)
    score = min(title_matches * 0.25, 0.5)

    summary_matches = sum(1 for kw in keywords if kw in summary_lower)
    score += min(summary_matches * 0.05, 0.2)

    # Recency — normaliser la date en UTC naive pour le calcul
    if published_date.tzinfo is not None:
        pub_naive = published_date.astimezone(timezone.utc).replace(tzinfo=None)
    else:
        pub_naive = published_date
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    age_days = max(0.0, (now_naive - pub_naive).total_seconds() / 86400)
    score += 0.3 * math.exp(-0.1 * age_days)

    return min(score, 1.0)


# ── Date parsing ──────────────────────────────────────────────────────────────

def parse_date(date_str: str) -> datetime:
    """
    Parse RFC 2822 (RSS pubDate) ou ISO 8601 (Atom).
    Retourne datetime UTC naive. Si échec → datetime.utcnow().
    """
    if not date_str:
        return datetime.utcnow()
    # RFC 2822 (ex: "Tue, 15 Apr 2026 12:00:00 +0000")
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    except Exception:
        pass
    # ISO 8601 (ex: "2026-04-15T12:00:00Z" ou "2026-04-15")
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
        try:
            input_str = date_str[:10] if fmt == "%Y-%m-%d" else date_str
            dt = datetime.strptime(input_str, fmt)
            return dt.replace(tzinfo=None) if dt.tzinfo is None else dt.astimezone(timezone.utc).replace(tzinfo=None)
        except ValueError:
            continue
    return datetime.utcnow()


# ── RSS parsing ───────────────────────────────────────────────────────────────

# Namespaces courants dans les feeds Atom/RSS
_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
}


def _text(el, *tags) -> str:
    """Cherche le premier tag non-vide parmi les candidats. Retourne '' si rien."""
    for tag in tags:
        child = el.find(tag)
        if child is not None and child.text:
            return child.text.strip()
    return ""


def parse_rss_content(xml_bytes: bytes) -> list:
    """
    Parse du contenu RSS/Atom brut (bytes).
    Retourne une liste de dicts : {title, url, summary, published_date}.
    Retourne [] si le XML est invalide ou vide.
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return []

    articles = []

    # Format RSS 2.0 : <rss><channel><item>
    for item in root.iter("item"):
        title = _text(item, "title")
        url = _text(item, "link")
        summary = _text(item, "description",
                        f"{{{_NS['content']}}}encoded")
        pub_date = _text(item, "pubDate",
                         f"{{{_NS['dc']}}}date")
        if not title or not url:
            continue
        articles.append({
            "title": title,
            "url": url,
            "summary": re.sub(r"<[^>]+>", " ", summary)[:500],
            "published_date": parse_date(pub_date),
        })

    # Format Atom : <feed><entry>
    for entry in root.iter(f"{{{_NS['atom']}}}entry"):
        title_el = entry.find(f"{{{_NS['atom']}}}title")
        link_el = (entry.find(f"{{{_NS['atom']}}}link[@rel='alternate']") or
                   entry.find(f"{{{_NS['atom']}}}link"))
        summary_el = (entry.find(f"{{{_NS['atom']}}}summary") or
                      entry.find(f"{{{_NS['atom']}}}content"))
        updated_el = (entry.find(f"{{{_NS['atom']}}}updated") or
                      entry.find(f"{{{_NS['atom']}}}published"))

        title = title_el.text.strip() if title_el is not None and title_el.text else ""
        url = link_el.get("href", "") if link_el is not None else ""
        summary = summary_el.text or "" if summary_el is not None else ""
        pub_date = updated_el.text or "" if updated_el is not None else ""

        if not title or not url:
            continue
        articles.append({
            "title": title,
            "url": url,
            "summary": re.sub(r"<[^>]+>", " ", summary)[:500],
            "published_date": parse_date(pub_date),
        })

    return articles


def fetch_rss(url: str, timeout: int = FETCH_TIMEOUT) -> list:
    """
    Fetch + parse un feed RSS/Atom depuis une URL.
    Retourne [] si timeout, erreur réseau ou XML invalide.
    """
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PractitionerCollector/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read()
        return parse_rss_content(content)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, http.client.HTTPException) as e:
        print(f"[SKIP] {url}: {e}")
        return []


# ── Hacker News (Algolia) ─────────────────────────────────────────────────────

HN_ALGOLIA = "https://hn.algolia.com/api/v1/search"


def fetch_hn(domain: str, since_days: int = DEFAULT_SINCE,
             timeout: int = FETCH_TIMEOUT) -> list:
    """
    Fetch les top stories HN filtrées par domaine via Algolia API.
    Retourne [] si erreur réseau ou réponse invalide.
    Filtre : score HN >= HN_MIN_POINTS.
    Déduplication interne par URL (une même story peut matcher plusieurs keywords).
    """
    keywords = DOMAIN_HN_KEYWORDS.get(domain, [])
    since_ts = int(datetime.now(timezone.utc).timestamp()) - since_days * 86400

    articles = []
    seen_urls: set = set()

    for keyword in keywords:
        params = urllib.parse.urlencode({
            "tags": "story",
            "query": keyword,
            "numericFilters": f"created_at_i>{since_ts}",
            "hitsPerPage": 10,
        })
        algolia_url = f"{HN_ALGOLIA}?{params}"
        try:
            req = urllib.request.Request(
                algolia_url, headers={"User-Agent": "PractitionerCollector/1.0"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read())
        except (urllib.error.URLError, urllib.error.HTTPError,
                OSError, http.client.HTTPException, json.JSONDecodeError) as e:
            print(f"[SKIP HN] {keyword}: {e}")
            continue

        for hit in data.get("hits", []):
            points = hit.get("points") or 0
            if points < HN_MIN_POINTS:
                continue
            url_story = hit.get("url") or (
                f"https://news.ycombinator.com/item?id={hit['objectID']}"
                if hit.get("objectID") else None
            )
            if not url_story:
                continue
            if url_story in seen_urls:
                continue
            seen_urls.add(url_story)

            created_ts = hit.get("created_at_i") or 0
            pub_date = (datetime.fromtimestamp(created_ts, tz=timezone.utc).replace(tzinfo=None)
                        if created_ts > 0 else datetime.utcnow())

            articles.append({
                "title": hit.get("title", ""),
                "url": url_story,
                "summary": (hit.get("story_text") or "")[:500],
                "published_date": pub_date,
            })

    return articles


# ── Paper ID + Frontmatter ────────────────────────────────────────────────────

def prac_paper_id(url: str) -> str:
    """Génère un paper_id stable depuis l'URL. Préfixe 'prac-' (8 hex chars)."""
    return PRAC_PREFIX + hashlib.md5(url.encode("utf-8"), usedforsecurity=False).hexdigest()[:8]


def format_as_markdown(article: dict, domain: str) -> str:
    """
    Convertit un article praicien en markdown avec frontmatter compatible paper_synthesizer.py.
    Champs identiques à corpus_collector.py : type, domain, paper_id, source, source_url,
    title, date, relevance_score, tier, keywords, collected.
    """
    title = article.get("title", "")
    url = article.get("url", "")
    summary = article.get("summary", "") or "(résumé non disponible)"
    paper_id = article.get("paper_id") or prac_paper_id(url)
    score = article.get("relevance_score", 0.0)
    tier = article.get("tier", "B")
    keywords = article.get("keywords", [])
    pub_date = article.get("published_date")
    date_str = pub_date.strftime("%Y-%m-%d") if pub_date else datetime.utcnow().strftime("%Y-%m-%d")
    collected = datetime.utcnow().strftime("%Y-%m-%d")

    # Escape double quotes in title to avoid YAML breakage
    title_safe = title.replace('"', "'")

    kw_yaml = "\n".join(f'  - "{k}"' for k in keywords)
    kw_block = f"\n{kw_yaml}" if kw_yaml else " []"

    return f"""---
type: paper
domain: {domain}
paper_id: "{paper_id}"
source: practitioner
source_url: "{url}"
title: "{title_safe}"
date: "{date_str}"
relevance_score: {round(score, 4)}
tier: {tier}
keywords:{kw_block}
collected: "{collected}"
---

# {title}

**Résumé :** {summary[:800]}

**Source :** practitioner · {date_str}

<!-- source-url: {url} -->
"""


# ── Déduplication ─────────────────────────────────────────────────────────────

def load_seen_ids(seen_ids_file: Path = None) -> set:
    """Charge les paper_ids déjà vus depuis le fichier partagé avec corpus_collector.py."""
    f = seen_ids_file or SEEN_IDS_FILE
    if not f.exists():
        return set()
    lines = f.read_text(encoding="utf-8").splitlines()
    return {line.strip() for line in lines if line.strip()}


def save_seen_ids(seen: set, seen_ids_file: Path = None) -> None:
    """Persiste les paper_ids vus. Écriture atomique via .tmp + os.replace()."""
    f = seen_ids_file or SEEN_IDS_FILE
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".tmp")
    tmp.write_text("\n".join(sorted(seen)) + "\n", encoding="utf-8")
    os.replace(tmp, f)


# ── Sauvegarde ────────────────────────────────────────────────────────────────

def save_articles(articles: list, domain: str, seen_ids: set,
                  min_score: float = DEFAULT_MIN_SCORE,
                  raw_dir: Path = None, dry_run: bool = False) -> dict:
    """
    Score, filtre et sauvegarde les articles praiciens.

    Returns stats: {saved, duplicates, tier_c_filtered, would_save, tier_counts}.
    seen_ids is mutated in-place — caller must persist with save_seen_ids().
    """
    out_dir = (raw_dir or RAW_DIR) / domain
    if not dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    stats = {
        "saved": 0,
        "duplicates": 0,
        "tier_c_filtered": 0,
        "would_save": 0,
        "tier_counts": {"S": 0, "A": 0, "B": 0, "C": 0},
    }

    for article in articles:
        url = article.get("url", "")
        if not url or not article.get("title"):
            continue

        paper_id = prac_paper_id(url)
        if paper_id in seen_ids:
            stats["duplicates"] += 1
            continue

        score = score_article(
            title=article.get("title", ""),
            summary=article.get("summary", ""),
            domain=domain,
            published_date=article.get("published_date", datetime.utcnow()),
        )
        tier = score_to_tier(score)
        stats["tier_counts"][tier] += 1

        if score < min_score:
            stats["tier_c_filtered"] += 1
            continue

        article = dict(article)  # avoid mutating caller's dict
        article["paper_id"] = paper_id
        article["relevance_score"] = score
        article["tier"] = tier
        article["keywords"] = [
            kw for kw in DOMAIN_FALLBACK_KEYWORDS.get(domain, [])
            if kw in (article.get("title", "") + " " + article.get("summary", "")).lower()
        ][:5]

        if dry_run:
            print(f"[DRY-RUN] {tier} {score:.2f} — {article['title'][:80]}")
            stats["would_save"] += 1
            seen_ids.add(paper_id)
            continue

        slug = re.sub(r"[^\w]", "_", article["title"][:50].lower()).strip("_")
        date_str = article.get("published_date", datetime.utcnow()).strftime("%Y-%m-%d")
        fname = out_dir / f"{date_str}_{slug}.md"

        if not fname.exists():
            fname.write_text(format_as_markdown(article, domain), encoding="utf-8")
            stats["saved"] += 1
            seen_ids.add(paper_id)

    return stats
