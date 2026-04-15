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
