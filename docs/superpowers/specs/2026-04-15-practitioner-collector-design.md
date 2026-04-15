# Design — Practitioner Collector

**Date :** 2026-04-15
**Statut :** APPROVED — prêt pour implémentation
**Auteur :** Djemil David

---

## Contexte

Le pipeline corpus actuel (`corpus_collector.py`) collecte exclusivement des papers académiques via arXiv et Semantic Scholar. Pour un architecte solution cloud, les savoirs les plus actionnables viennent de sources praicitiennes : blogs officiels (GCP, Firebase, CNCF), praticiens reconnus (Martin Fowler, InfoQ), et communauté (HN top stories).

`practitioner_collector.py` ajoute ce flux sans modifier le pipeline existant — il produit des fichiers dans le même format frontmatter que `corpus_collector.py`, transparents pour `paper_synthesizer.py`.

---

## Architecture

```
practitioner_collector.py
├── DOMAINS_RSS         dict: domain → [feed URLs]
├── DOMAIN_HN_KEYWORDS  dict: domain → [keywords HN]
├── fetch_rss()         urllib + xml.etree → list[Article]
├── fetch_hn()          Algolia API → list[Article]
├── score_article()     pertinence 0.0–1.0
├── format_as_markdown() → frontmatter compatible paper_synthesizer
├── save_articles()     → _inbox/raw/papers/{domain}/*.md
└── main()              argparse CLI
```

**Dépendances :** zéro dépendance externe — stdlib uniquement (`urllib`, `xml.etree`, `json`, `hashlib`, `argparse`, `math`).

---

## Sources

### RSS par domaine

```python
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
```

### Hacker News (Algolia API)

```python
DOMAIN_HN_KEYWORDS = {
    "gcp":            ["gcp", "google cloud", "cloud run", "bigquery", "vertex ai"],
    "firebase":       ["firebase", "firestore", "app check"],
    "cloud-native":   ["kubernetes", "k8s", "istio", "cncf", "platform engineering"],
    "architecture":   ["distributed systems", "event-driven", "ddd", "microservices"],
    "devops":         ["terraform", "gitops", "ci/cd", "pulumi", "iac"],
    "ai-engineering": ["llmops", "rag", "llm", "prompt engineering", "agents"],
    "security":       ["zero trust", "iam", "owasp", "cloud security"],
}
```

Endpoint : `https://hn.algolia.com/api/v1/search?tags=story&query={keyword}&numericFilters=created_at_i>{since_ts}`
Filtre qualité : score HN ≥ 50 points minimum.
Top 10 résultats par keyword.

---

## Collecte & déduplication

**Fenêtre temporelle :** `--since 7` (7 derniers jours, configurable).

**Déduplication :** même fichier `_logs/seen-paper-ids.txt` que `corpus_collector.py`.
- `paper_id = "prac-" + hashlib.md5(url.encode()).hexdigest()[:8]`
- Préfixe `prac-` distingue les IDs praiciens des arxiv IDs.
- Un article déjà vu n'est pas re-sauvegardé, même cross-domaine.

---

## Scoring (0.0–1.0)

```python
score = 0.0

# Keyword match titre (signal fort)
title_matches = count_keywords(title, domain_keywords)
score += min(title_matches * 0.25, 0.5)

# Keyword match résumé (signal faible)
summary_matches = count_keywords(summary, domain_keywords)
score += min(summary_matches * 0.05, 0.2)

# Recency (décroissance exponentielle)
age_days = (now - published_date).days
score += 0.3 * exp(-0.1 * age_days)

# Tier
# S ≥ 0.7 | A ≥ 0.5 | B ≥ 0.3 | C < 0.3 (ignoré silencieusement)
```

`DOMAIN_FALLBACK_KEYWORDS` par domaine utilisé si keywords explicites manquants.

---

## Frontmatter produit

Compatible `paper_synthesizer.py` sans modification du synthesizer.

```yaml
---
type: paper
domain: gcp
paper_id: "prac-a3f2c1b8"
source: practitioner
source_url: "https://cloud.google.com/blog/..."
title: "Introducing Cloud Run Jobs"
date: "2026-04-14"
relevance_score: 0.72
tier: A
keywords:
  - "cloud run"
  - "serverless"
collected: "2026-04-15"
---

# Titre de l'article

**Résumé :** ...

**Source :** practitioner · 2026-04-14
<!-- source-url: https://... -->
```

---

## CLI

```bash
# Tous les domaines, 7 jours (défaut)
python3 practitioner_collector.py

# Domaine ciblé
python3 practitioner_collector.py --domain gcp

# Fenêtre personnalisée
python3 practitioner_collector.py --since 3

# Dry-run : affiche ce qui serait collecté, n'écrit rien
python3 practitioner_collector.py --dry-run

# Force re-collecte même si déjà vu (utile pour debug)
python3 practitioner_collector.py --force

# Max articles par domaine
python3 practitioner_collector.py --max 20
```

---

## Intégration nightly-agent.sh

Ajout après l'appel existant à `corpus_collector.py` :

```bash
# Collecte praicienne — weekends automatique + FORCE_PRACTITIONER manuel
if [ "${FORCE_PRACTITIONER:-0}" = "1" ] || is_weekend; then
    python3 "$VAULT/practitioner_collector.py" --since 7 >> "$LOG" 2>&1 || true
fi
```

`is_weekend` = fonction shell vérifiant `$(date +%u)` ∈ {6, 7}.

Manuel sans attendre le nightly :
```bash
FORCE_PRACTITIONER=1 bash nightly-agent.sh
# ou directement :
python3 practitioner_collector.py --domain gcp --dry-run
```

---

## Gestion d'erreurs

- **Feed RSS en timeout/erreur** → log `SKIP {url}: {reason}` + continue (pas de crash)
- **Feed mal formé (XML invalide)** → `ET.ParseError` capturé → skip propre
- **HN API down** → skip du bloc HN, RSS continue normalement
- **Timeout par feed** : 10 secondes strict (`urllib` timeout)
- **Aucun article collecté** → exit 0 propre (pas d'erreur, juste un log INFO)

---

## Tests

Fichier : `tests/test_practitioner_collector.py`

| Test | Ce qu'il vérifie |
|---|---|
| `test_parse_rss_valid` | Feed RSS valide → articles extraits correctement |
| `test_parse_rss_malformed` | XML invalide → skip propre, aucun crash |
| `test_score_keyword_match` | Article titre GCP → score > 0.5 |
| `test_score_no_match` | Article hors-domaine → score < 0.3 (tier C) |
| `test_dedup_seen_ids` | URL déjà dans seen_ids → non sauvegardée |
| `test_format_frontmatter` | Frontmatter produit contient tous les champs requis |
| `test_dry_run` | `--dry-run` → zéro fichier écrit sur disque |

---

## Ce qu'on ne fait pas

- Pas de dépendance externe (`feedparser`, `requests`, etc.) — stdlib uniquement
- Pas de config YAML externe — sources hardcodées comme `corpus_collector.py`
- Pas de Semantic Scholar pour les sources praicitiennes (API académique)
- Pas de re-synthèse automatique — `paper_synthesizer.py` tourne séparément comme aujourd'hui
- Pas de modification de `paper_synthesizer.py` — frontmatter compatible by design

---

## Références

- `corpus_collector.py` — modèle de structure à suivre
- `paper_synthesizer.py` — consommateur du frontmatter produit
- `nightly-agent.sh` — point d'intégration
- `_logs/seen-paper-ids.txt` — déduplication partagée
