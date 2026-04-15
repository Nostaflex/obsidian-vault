# Practitioner Collector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `practitioner_collector.py` — collecte RSS + HN pour 7 domaines architecte solution cloud, sortie frontmatter compatible `paper_synthesizer.py`, intégré dans `nightly-agent.sh`.

**Architecture:** Script standalone miroir de `corpus_collector.py`. Fetch RSS (stdlib `urllib` + `xml.etree`) + Hacker News (Algolia API JSON). Score par keyword match + recency decay. Output `_inbox/raw/papers/{domain}/*.md` transparent pour `paper_synthesizer.py`. Déduplication partagée via `seen-paper-ids.txt`.

**Tech Stack:** Python 3.9+, stdlib uniquement (`urllib`, `xml.etree`, `json`, `hashlib`, `math`, `argparse`). Pytest pour les tests.

---

## File Structure

| Fichier | Action | Responsabilité |
|---|---|---|
| `practitioner_collector.py` | Créer | Script principal — fetch, score, save |
| `tests/test_practitioner_collector.py` | Créer | 7 tests unitaires TDD |
| `tests/fixtures/sample_rss.xml` | Créer | Fixture RSS pour tests |
| `nightly-agent.sh` | Modifier | Ajouter is_weekend + FORCE_PRACTITIONER block |

---

## Task 1: Skeleton + constantes

**Files:**
- Create: `practitioner_collector.py`

- [ ] **Step 1: Créer le fichier avec imports et constantes**

```python
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
```

- [ ] **Step 2: Vérifier que le fichier s'importe sans erreur**

```bash
cd ~/Documents/Obsidian/KnowledgeBase
python3 -c "import practitioner_collector; print('OK')"
```

Attendu : `OK`

- [ ] **Step 3: Commit**

```bash
git add practitioner_collector.py
git commit -m "feat(practitioner-collector): skeleton — imports, constants, domain config"
```

---

## Task 2: Scoring article

**Files:**
- Modify: `practitioner_collector.py`
- Create: `tests/test_practitioner_collector.py`

- [ ] **Step 1: Créer la fixture RSS et le fichier de test**

Créer `tests/fixtures/sample_rss.xml` :

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Deploying to Cloud Run with Terraform</title>
      <link>https://example.com/cloud-run-terraform</link>
      <description>A guide to deploying GCP Cloud Run services using Terraform IaC patterns.</description>
      <pubDate>Mon, 14 Apr 2026 10:00:00 +0000</pubDate>
    </item>
    <item>
      <title>Recipe: The Perfect Sourdough Bread</title>
      <link>https://example.com/sourdough</link>
      <description>How to bake a perfect sourdough loaf at home.</description>
      <pubDate>Mon, 14 Apr 2026 10:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>
```

Créer `tests/test_practitioner_collector.py` :

```python
# tests/test_practitioner_collector.py
import sys
import json
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
import urllib.error

sys.path.insert(0, str(Path(__file__).parent.parent))

import practitioner_collector as pc


class TestScoreArticle:
    def _now(self):
        return datetime.now(timezone.utc)

    def test_keyword_match_in_title_raises_score(self):
        published = self._now() - timedelta(hours=1)
        score = pc.score_article(
            title="Deploying to Cloud Run with Terraform",
            summary="A guide to GCP Cloud Run.",
            domain="gcp",
            published_date=published,
        )
        assert score >= 0.5, f"Expected score >= 0.5 for GCP title match, got {score}"

    def test_no_keyword_match_gives_low_score(self):
        published = self._now() - timedelta(hours=1)
        score = pc.score_article(
            title="Recipe: The Perfect Sourdough Bread",
            summary="How to bake a perfect sourdough loaf at home.",
            domain="gcp",
            published_date=published,
        )
        assert score < 0.3, f"Expected score < 0.3 for off-domain content, got {score}"

    def test_old_article_gets_recency_penalty(self):
        recent = self._now() - timedelta(hours=1)
        old = self._now() - timedelta(days=30)
        score_recent = pc.score_article("Cloud Run Guide", "GCP Cloud Run tutorial", "gcp", recent)
        score_old = pc.score_article("Cloud Run Guide", "GCP Cloud Run tutorial", "gcp", old)
        assert score_recent > score_old, "Recent article should score higher than old one"

    def test_score_capped_at_1(self):
        published = self._now()
        # Stuff title and summary with lots of keywords
        score = pc.score_article(
            title="gcp cloud run gke bigquery vertex ai cloud sql",
            summary="gcp google cloud cloud run gke bigquery vertex ai pubsub spanner cloud sql cloud functions",
            domain="gcp",
            published_date=published,
        )
        assert score <= 1.0
```

- [ ] **Step 2: Lancer les tests — vérifier qu'ils échouent (fonctions pas encore définies)**

```bash
cd ~/Documents/Obsidian/KnowledgeBase
python3 -m pytest tests/test_practitioner_collector.py::TestScoreArticle -v 2>&1 | head -20
```

Attendu : `AttributeError: module 'practitioner_collector' has no attribute 'score_article'`

- [ ] **Step 3: Implémenter `score_article()` dans `practitioner_collector.py`**

Ajouter après les constantes :

```python
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
    Score de pertinence 0.0–1.0 pour un article praicien.

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
    age_days = max(0, (now_naive - pub_naive).days)
    score += 0.3 * math.exp(-0.1 * age_days)

    return min(score, 1.0)
```

- [ ] **Step 4: Lancer les tests — vérifier qu'ils passent**

```bash
python3 -m pytest tests/test_practitioner_collector.py::TestScoreArticle -v
```

Attendu : `4 passed`

- [ ] **Step 5: Commit**

```bash
git add practitioner_collector.py tests/test_practitioner_collector.py tests/fixtures/sample_rss.xml
git commit -m "feat(practitioner-collector): score_article() — keyword match + recency decay + tests"
```

---

## Task 3: Parsing RSS

**Files:**
- Modify: `practitioner_collector.py`
- Modify: `tests/test_practitioner_collector.py`

- [ ] **Step 1: Écrire le test de parsing RSS (append dans le fichier de test)**

Ajouter dans `tests/test_practitioner_collector.py` :

```python
class TestParseRss:
    FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_rss.xml"

    def test_parse_valid_rss_returns_articles(self):
        xml_content = self.FIXTURE_PATH.read_bytes()
        articles = pc.parse_rss_content(xml_content)
        assert len(articles) == 2
        assert articles[0]["title"] == "Deploying to Cloud Run with Terraform"
        assert articles[0]["url"] == "https://example.com/cloud-run-terraform"
        assert "cloud run" in articles[0]["summary"].lower()
        assert isinstance(articles[0]["published_date"], datetime)

    def test_parse_malformed_xml_returns_empty(self):
        malformed = b"<rss><channel><item><title>Broken</title>"  # not closed
        articles = pc.parse_rss_content(malformed)
        assert articles == []

    def test_parse_empty_feed_returns_empty(self):
        empty = b'<?xml version="1.0"?><rss version="2.0"><channel></channel></rss>'
        articles = pc.parse_rss_content(empty)
        assert articles == []
```

- [ ] **Step 2: Lancer les tests — vérifier qu'ils échouent**

```bash
python3 -m pytest tests/test_practitioner_collector.py::TestParseRss -v 2>&1 | head -10
```

Attendu : `AttributeError: module 'practitioner_collector' has no attribute 'parse_rss_content'`

- [ ] **Step 3: Implémenter `parse_rss_content()` et `fetch_rss()` dans `practitioner_collector.py`**

```python
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
            dt = datetime.strptime(date_str[:19], fmt[:len(date_str[:19])])
            return dt
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
            "summary": re.sub(r"<[^>]+>", " ", summary)[:500],  # strip HTML tags
            "published_date": parse_date(pub_date),
        })

    # Format Atom : <feed><entry>
    for entry in root.iter(f"{{{_NS['atom']}}}entry"):
        title_el = entry.find(f"{{{_NS['atom']}}}title")
        link_el = entry.find(f"{{{_NS['atom']}}}link[@rel='alternate']") or \
                  entry.find(f"{{{_NS['atom']}}}link")
        summary_el = entry.find(f"{{{_NS['atom']}}}summary") or \
                     entry.find(f"{{{_NS['atom']}}}content")
        updated_el = entry.find(f"{{{_NS['atom']}}}updated") or \
                     entry.find(f"{{{_NS['atom']}}}published")

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
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        print(f"[SKIP] {url}: {e}")
        return []
```

- [ ] **Step 4: Lancer les tests RSS — vérifier qu'ils passent**

```bash
python3 -m pytest tests/test_practitioner_collector.py::TestParseRss -v
```

Attendu : `3 passed`

- [ ] **Step 5: Lancer tous les tests existants — vérifier aucune régression**

```bash
python3 -m pytest tests/test_practitioner_collector.py -v
```

Attendu : `7 passed` (4 scoring + 3 RSS)

- [ ] **Step 6: Commit**

```bash
git add practitioner_collector.py tests/test_practitioner_collector.py tests/fixtures/sample_rss.xml
git commit -m "feat(practitioner-collector): parse_rss_content() + fetch_rss() — RSS/Atom parser + tests"
```

---

## Task 4: Fetch Hacker News (Algolia API)

**Files:**
- Modify: `practitioner_collector.py`
- Modify: `tests/test_practitioner_collector.py`

- [ ] **Step 1: Écrire les tests HN (append dans le fichier de test)**

```python
class TestFetchHn:
    def _make_hn_response(self, hits: list) -> bytes:
        return json.dumps({"hits": hits}).encode()

    def test_fetch_hn_returns_articles_above_min_points(self):
        hits = [
            {"title": "How we scaled Firestore at Firebase", "url": "https://firebase.blog/scale",
             "objectID": "111", "points": 120,
             "created_at_i": int(datetime.now(timezone.utc).timestamp()) - 3600,
             "story_text": ""},
            {"title": "Low quality post", "url": "https://example.com/low",
             "objectID": "222", "points": 10,
             "created_at_i": int(datetime.now(timezone.utc).timestamp()) - 3600,
             "story_text": ""},
        ]
        response_bytes = self._make_hn_response(hits)

        with patch("urllib.request.urlopen") as mock_open:
            mock_resp = MagicMock()
            mock_resp.read.return_value = response_bytes
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_open.return_value = mock_resp

            articles = pc.fetch_hn("firebase", since_days=7)

        assert len(articles) == 1
        assert articles[0]["title"] == "How we scaled Firestore at Firebase"

    def test_fetch_hn_network_error_returns_empty(self):
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
            articles = pc.fetch_hn("firebase", since_days=7)
        assert articles == []
```

- [ ] **Step 2: Lancer les tests HN — vérifier qu'ils échouent**

```bash
python3 -m pytest tests/test_practitioner_collector.py::TestFetchHn -v 2>&1 | head -10
```

Attendu : `AttributeError: module 'practitioner_collector' has no attribute 'fetch_hn'`

- [ ] **Step 3: Implémenter `fetch_hn()` dans `practitioner_collector.py`**

```python
# ── Hacker News (Algolia) ─────────────────────────────────────────────────────

HN_ALGOLIA = "https://hn.algolia.com/api/v1/search"


def fetch_hn(domain: str, since_days: int = DEFAULT_SINCE,
             timeout: int = FETCH_TIMEOUT) -> list:
    """
    Fetch les top stories HN filtrées par domaine via Algolia API.
    Retourne [] si erreur réseau ou réponse invalide.
    Filtre : score HN >= HN_MIN_POINTS.
    """
    keywords = DOMAIN_HN_KEYWORDS.get(domain, [])
    since_ts = int((datetime.now(timezone.utc).timestamp()) - since_days * 86400)

    articles = []
    seen_urls: set = set()

    for keyword in keywords:
        params = urllib.parse.urlencode({
            "tags": "story",
            "query": keyword,
            "numericFilters": f"created_at_i>{since_ts}",
            "hitsPerPage": 10,
        })
        url = f"{HN_ALGOLIA}?{params}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PractitionerCollector/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read())
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, json.JSONDecodeError) as e:
            print(f"[SKIP HN] {keyword}: {e}")
            continue

        for hit in data.get("hits", []):
            points = hit.get("points") or 0
            if points < HN_MIN_POINTS:
                continue
            url_story = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID','')}"
            if url_story in seen_urls:
                continue
            seen_urls.add(url_story)

            created_ts = hit.get("created_at_i", 0)
            pub_date = datetime.fromtimestamp(created_ts, tz=timezone.utc).replace(tzinfo=None)

            articles.append({
                "title": hit.get("title", ""),
                "url": url_story,
                "summary": (hit.get("story_text") or "")[:500],
                "published_date": pub_date,
            })

    return articles
```

- [ ] **Step 4: Lancer les tests HN — vérifier qu'ils passent**

```bash
python3 -m pytest tests/test_practitioner_collector.py::TestFetchHn -v
```

Attendu : `2 passed`

- [ ] **Step 5: Commit**

```bash
git add practitioner_collector.py tests/test_practitioner_collector.py
git commit -m "feat(practitioner-collector): fetch_hn() — Algolia API HN top stories + tests"
```

---

## Task 5: Format frontmatter + paper_id

**Files:**
- Modify: `practitioner_collector.py`
- Modify: `tests/test_practitioner_collector.py`

- [ ] **Step 1: Écrire le test frontmatter (append)**

```python
class TestFormatAsMarkdown:
    def _make_article(self, **kwargs):
        defaults = {
            "title": "Cloud Run: Zero to Production",
            "url": "https://cloud.google.com/blog/cloud-run",
            "summary": "A deep dive into Cloud Run deployment patterns.",
            "published_date": datetime(2026, 4, 14, 10, 0, 0),
            "relevance_score": 0.72,
            "tier": "A",
            "keywords": ["cloud run", "serverless"],
            "paper_id": "prac-a3f2c1b8",
        }
        defaults.update(kwargs)
        return defaults

    def test_frontmatter_contains_required_fields(self):
        article = self._make_article()
        md = pc.format_as_markdown(article, domain="gcp")
        assert "type: paper" in md
        assert "domain: gcp" in md
        assert 'paper_id: "prac-' in md
        assert "source: practitioner" in md
        assert "relevance_score: 0.72" in md
        assert "tier: A" in md
        assert "Cloud Run: Zero to Production" in md
```

- [ ] **Step 2: Lancer le test — vérifier qu'il échoue**

```bash
python3 -m pytest tests/test_practitioner_collector.py::TestFormatAsMarkdown -v 2>&1 | head -10
```

Attendu : `AttributeError: module 'practitioner_collector' has no attribute 'format_as_markdown'`

- [ ] **Step 3: Implémenter `prac_paper_id()` et `format_as_markdown()` dans `practitioner_collector.py`**

```python
# ── Paper ID + Frontmatter ────────────────────────────────────────────────────

def prac_paper_id(url: str) -> str:
    """Génère un paper_id stable depuis l'URL. Préfixe 'prac-' pour distinguer des arxiv IDs."""
    return PRAC_PREFIX + hashlib.md5(url.encode("utf-8"), usedforsecurity=False).hexdigest()[:8]


def format_as_markdown(article: dict, domain: str) -> str:
    """
    Convertit un article praicien en markdown avec frontmatter compatible paper_synthesizer.py.
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

    kw_yaml = "\n".join(f'  - "{k}"' for k in keywords)
    kw_block = f"\n{kw_yaml}" if kw_yaml else " []"

    return f"""---
type: paper
domain: {domain}
paper_id: "{paper_id}"
source: practitioner
source_url: "{url}"
title: "{title.replace('"', "'")}"
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
```

- [ ] **Step 4: Lancer le test frontmatter — vérifier qu'il passe**

```bash
python3 -m pytest tests/test_practitioner_collector.py::TestFormatAsMarkdown -v
```

Attendu : `1 passed`

- [ ] **Step 5: Commit**

```bash
git add practitioner_collector.py tests/test_practitioner_collector.py
git commit -m "feat(practitioner-collector): prac_paper_id() + format_as_markdown() — frontmatter compatible synthesizer"
```

---

## Task 6: Save articles + déduplication

**Files:**
- Modify: `practitioner_collector.py`
- Modify: `tests/test_practitioner_collector.py`

- [ ] **Step 1: Écrire les tests save + dedup (append)**

```python
class TestSaveArticles:
    def _make_article(self, url="https://cloud.google.com/blog/test"):
        return {
            "title": "Cloud Run Best Practices",
            "url": url,
            "summary": "Best practices for Cloud Run on GCP.",
            "published_date": datetime(2026, 4, 14, 10, 0, 0),
        }

    def test_save_article_creates_file(self, tmp_path):
        seen: set = set()
        articles = [self._make_article()]
        stats = pc.save_articles(articles, "gcp", seen, min_score=0.0, raw_dir=tmp_path)
        assert stats["saved"] == 1
        files = list((tmp_path / "gcp").glob("*.md"))
        assert len(files) == 1

    def test_duplicate_article_not_saved_twice(self, tmp_path):
        seen: set = set()
        articles = [self._make_article()]
        pc.save_articles(articles, "gcp", seen, min_score=0.0, raw_dir=tmp_path)
        stats2 = pc.save_articles(articles, "gcp", seen, min_score=0.0, raw_dir=tmp_path)
        assert stats2["saved"] == 0
        assert stats2["duplicates"] == 1

    def test_tier_c_article_not_saved(self, tmp_path):
        seen: set = set()
        articles = [{
            "title": "Recipe: Sourdough Bread",
            "url": "https://example.com/sourdough",
            "summary": "How to bake sourdough.",
            "published_date": datetime(2026, 4, 14),
        }]
        stats = pc.save_articles(articles, "gcp", seen, min_score=0.3, raw_dir=tmp_path)
        assert stats["saved"] == 0
        assert stats["tier_c_filtered"] == 1

    def test_dry_run_does_not_write_files(self, tmp_path):
        seen: set = set()
        articles = [self._make_article()]
        stats = pc.save_articles(articles, "gcp", seen, min_score=0.0,
                                 raw_dir=tmp_path, dry_run=True)
        files = list(tmp_path.glob("**/*.md"))
        assert len(files) == 0
        assert stats["saved"] == 0
        assert stats["would_save"] == 1
```

- [ ] **Step 2: Lancer les tests save — vérifier qu'ils échouent**

```bash
python3 -m pytest tests/test_practitioner_collector.py::TestSaveArticles -v 2>&1 | head -10
```

Attendu : `AttributeError: module 'practitioner_collector' has no attribute 'save_articles'`

- [ ] **Step 3: Implémenter `load_seen_ids()`, `save_seen_ids()`, `save_articles()` dans `practitioner_collector.py`**

```python
# ── Déduplication ─────────────────────────────────────────────────────────────

def load_seen_ids(seen_ids_file: Path = None) -> set:
    """Charge les paper_ids déjà vus depuis le fichier partagé avec corpus_collector.py."""
    f = seen_ids_file or SEEN_IDS_FILE
    if not f.exists():
        return set()
    lines = f.read_text(encoding="utf-8").splitlines()
    return {line.strip() for line in lines if line.strip()}


def save_seen_ids(seen: set, seen_ids_file: Path = None) -> None:
    """Persiste l'ensemble des paper_ids vus (trié). Écriture atomique via .tmp + replace."""
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

    Retourne stats : {saved, duplicates, tier_c_filtered, would_save, tier_counts}.
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

        article["paper_id"] = paper_id
        article["relevance_score"] = score
        article["tier"] = tier
        article["keywords"] = [kw for kw in DOMAIN_FALLBACK_KEYWORDS.get(domain, [])
                                if kw in (article.get("title", "") + " " +
                                           article.get("summary", "")).lower()][:5]

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
```

- [ ] **Step 4: Lancer les tests save — vérifier qu'ils passent**

```bash
python3 -m pytest tests/test_practitioner_collector.py::TestSaveArticles -v
```

Attendu : `4 passed`

- [ ] **Step 5: Lancer toute la suite — vérifier aucune régression**

```bash
python3 -m pytest tests/test_practitioner_collector.py -v
```

Attendu : `14 passed`

- [ ] **Step 6: Commit**

```bash
git add practitioner_collector.py tests/test_practitioner_collector.py
git commit -m "feat(practitioner-collector): save_articles() — scoring, dedup, dry-run + tests"
```

---

## Task 7: main() CLI + orchestration

**Files:**
- Modify: `practitioner_collector.py`

- [ ] **Step 1: Implémenter `main()` dans `practitioner_collector.py`**

Ajouter en fin de fichier :

```python
# ── Logging ───────────────────────────────────────────────────────────────────

def _log(message: str) -> None:
    ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"{ts} | {message}")


# ── Main ──────────────────────────────────────────────────────────────────────

def run(domain_filter: str = None, since_days: int = DEFAULT_SINCE,
        max_per_domain: int = DEFAULT_MAX, min_score: float = DEFAULT_MIN_SCORE,
        dry_run: bool = False, force: bool = False,
        raw_dir: Path = None, seen_ids_file: Path = None) -> None:
    """Orchestration principale. Expose les paramètres pour les tests d'intégration."""
    targets = {domain_filter: DOMAINS_RSS[domain_filter]} \
        if domain_filter else DOMAINS_RSS

    seen_ids = load_seen_ids(seen_ids_file) if not force else set()

    total_saved = 0
    total_skipped = 0

    for domain, feeds in targets.items():
        _log(f"Domain {domain}: collecte RSS ({len(feeds)} feeds) …")
        articles = []

        for feed_url in feeds:
            fetched = fetch_rss(feed_url)
            _log(f"  {feed_url}: {len(fetched)} articles")
            articles.extend(fetched)

        # HN
        hn_articles = fetch_hn(domain, since_days=since_days)
        _log(f"  HN ({domain}): {len(hn_articles)} articles")
        articles.extend(hn_articles)

        # Tronquer
        articles = articles[:max_per_domain * 3]  # marge avant scoring

        stats = save_articles(articles, domain, seen_ids,
                              min_score=min_score, raw_dir=raw_dir, dry_run=dry_run)

        _log(f"  → saved={stats['saved']} dup={stats['duplicates']} "
             f"tier_c={stats['tier_c_filtered']} tiers={stats['tier_counts']}")
        total_saved += stats["saved"] + stats.get("would_save", 0)
        total_skipped += stats["duplicates"] + stats["tier_c_filtered"]

    if not dry_run and not force:
        save_seen_ids(seen_ids, seen_ids_file)

    _log(f"DONE | saved={total_saved} skipped={total_skipped}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collecte praicienne RSS+HN pour architecte solution cloud."
    )
    parser.add_argument("--domain", choices=list(DOMAINS_RSS.keys()),
                        help="Domaine ciblé (défaut: tous)")
    parser.add_argument("--since", type=int, default=DEFAULT_SINCE,
                        help=f"Fenêtre en jours (défaut: {DEFAULT_SINCE})")
    parser.add_argument("--max", type=int, default=DEFAULT_MAX, dest="max_per_domain",
                        help=f"Max articles par domaine (défaut: {DEFAULT_MAX})")
    parser.add_argument("--min-score", type=float, default=DEFAULT_MIN_SCORE,
                        help=f"Score minimum (défaut: {DEFAULT_MIN_SCORE})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Affiche sans écrire")
    parser.add_argument("--force", action="store_true",
                        help="Ignore seen_ids (re-collecte)")
    args = parser.parse_args()

    run(
        domain_filter=args.domain,
        since_days=args.since,
        max_per_domain=args.max_per_domain,
        min_score=args.min_score,
        dry_run=args.dry_run,
        force=args.force,
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke test CLI dry-run**

```bash
cd ~/Documents/Obsidian/KnowledgeBase
python3 practitioner_collector.py --domain gcp --dry-run --since 7
```

Attendu : output avec lignes `[DRY-RUN] ...` ou `[SKIP] ...` — pas de crash, pas de fichier écrit.

- [ ] **Step 3: Vérifier que toute la suite de tests passe toujours**

```bash
python3 -m pytest tests/test_practitioner_collector.py -v
```

Attendu : `14 passed`

- [ ] **Step 4: Commit**

```bash
git add practitioner_collector.py
git commit -m "feat(practitioner-collector): main() CLI — orchestration complète, argparse, dry-run, force"
```

---

## Task 8: Intégration nightly-agent.sh

**Files:**
- Modify: `nightly-agent.sh`

- [ ] **Step 1: Lire les lignes autour du bloc integrity_check dans nightly-agent.sh**

```bash
grep -n "integrity_check\|python3\|Terminé" ~/Documents/Obsidian/KnowledgeBase/nightly-agent.sh
```

Identifier la ligne après `python3 "$VAULT/integrity_check.py"` et avant le lancement de Claude.

- [ ] **Step 2: Ajouter le bloc practitioner_collector dans nightly-agent.sh**

Insérer après la ligne `python3 "$VAULT/integrity_check.py" >> "$LOG" 2>&1` et avant `# 2. Lancer l'agent nocturne` :

```bash
# 1b. Collecte praicienne (weekends automatique + FORCE_PRACTITIONER=1 pour run manuel)
_is_weekend() { day=$(date +%u); [ "$day" -ge 6 ]; }
if [ "${FORCE_PRACTITIONER:-0}" = "1" ] || _is_weekend; then
  echo "→ practitioner-collector..." >> "$LOG"
  python3 "$VAULT/practitioner_collector.py" --since 7 >> "$LOG" 2>&1 || \
    echo "⚠️  practitioner_collector a échoué (exit $?) — run nocturne continue" >> "$LOG"
fi
```

Note : `|| true` remplacé par `|| echo` pour logger l'échec sans interrompre le nightly (`set -euo pipefail` actif).

- [ ] **Step 3: Tester le bloc shell en isolation**

```bash
cd ~/Documents/Obsidian/KnowledgeBase
FORCE_PRACTITIONER=1 bash -c '
  source nightly-agent.sh 2>&1 | head -5
' 2>&1 | head -10
```

Si nightly démarre entièrement, couper avec Ctrl+C après les premières lignes de log — on vérifie juste que le bloc est syntaxiquement correct.

Alternative plus safe — valider la syntaxe uniquement :

```bash
bash -n ~/Documents/Obsidian/KnowledgeBase/nightly-agent.sh && echo "Syntax OK"
```

Attendu : `Syntax OK`

- [ ] **Step 4: Test manuel du collecteur seul**

```bash
python3 ~/Documents/Obsidian/KnowledgeBase/practitioner_collector.py --domain gcp --dry-run
```

Attendu : lignes de log sans crash. `[SKIP]` pour les feeds inaccessibles est normal.

- [ ] **Step 5: Commit final**

```bash
git add nightly-agent.sh
git commit -m "feat(practitioner-collector): intégration nightly — is_weekend + FORCE_PRACTITIONER block"
```

---

## Self-Review

**Spec coverage :**

| Requirement spec | Tâche |
|---|---|
| 7 domaines (gcp, firebase, cloud-native, architecture, devops, ai-engineering, security) | Task 1 — DOMAINS_RSS + DOMAIN_HN_KEYWORDS |
| RSS fetch stdlib | Task 3 — fetch_rss() |
| HN Algolia API | Task 4 — fetch_hn() |
| Scoring keyword + recency | Task 2 — score_article() |
| Frontmatter compatible paper_synthesizer | Task 5 — format_as_markdown() |
| Déduplication seen-paper-ids.txt partagée | Task 6 — save_articles() + load/save_seen_ids() |
| dry-run | Task 6 — flag dry_run dans save_articles() |
| CLI argparse | Task 7 — main() |
| Intégration nightly weekends + FORCE_PRACTITIONER | Task 8 — nightly-agent.sh |
| Timeout 10s par feed | Task 3 — FETCH_TIMEOUT constant |
| HN filtre ≥ 50 points | Task 4 — HN_MIN_POINTS |
| 7 tests unitaires | Tasks 2–6 — 14 tests au total |
| Zéro dépendance externe | Task 1 — stdlib uniquement |

**Placeholders :** aucun.

**Cohérence des types :**
- `score_article()` → `float` → utilisé dans `save_articles()` ✓
- `prac_paper_id()` → `str` → utilisé dans `save_articles()` + `format_as_markdown()` ✓
- `parse_rss_content()` → `list[dict]` → même format que `fetch_hn()` → même format attendu par `save_articles()` ✓
- `run()` expose `raw_dir` + `seen_ids_file` pour permettre les tests d'intégration sans toucher au filesystem de prod ✓
