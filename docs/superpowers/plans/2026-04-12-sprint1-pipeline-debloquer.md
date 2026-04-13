# Pipeline Second Brain — Sprint 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Débloquer le pipeline Second Brain (51 papers en backlog) et le rendre concurrent-safe, sans dépendance NotebookLM.

**Architecture:** Fix corpus_collector pour dédupliquer via clé canonique MD5 (papers Semantic Scholar sans ArXiv ID). Migrer paper_synthesizer de Gemini (bloqué EU) vers Claude Haiku Batch (fiable, ~$0.06/semaine). Rendre nightly-agent.sh concurrent-safe avec flock. Enrichir .nightly-prompt.md avec ceiling guard, overflow drain FIFO, et bootstrap cross-refs mode.

**Tech Stack:** Python 3.9, `anthropic` SDK (Messages Batches API), `pytest`, bash/flock (macOS/GNU coreutils), Obsidian vault markdown.

---

## File Map

| Fichier | Action | Responsabilité |
|---------|--------|----------------|
| `corpus_collector.py` | Modifier | Ajouter `canonical_paper_id()`, mettre à jour dédup, ajouter `paper_id` en frontmatter |
| `_logs/seen-paper-ids.txt` | Créer (migration auto) | Remplace `seen-arxiv-ids.txt`, clés canoniques toutes sources |
| `paper_synthesizer.py` | Modifier (API + naming) | Remplacer Gemini par Anthropic Batch, outputs `A-{paper_id_sanitized}-{n}.md` |
| `nightly-agent.sh` | Modifier | Ajouter flock concurrent guard avant le guard date |
| `.nightly-prompt.md` | Modifier | Étape 0: ceiling + overflow drain; Étape 2A: nouveau glob + naming; Étape 3: bootstrap; Étape 5: INDEX diff |
| `tests/test_corpus_collector.py` | Créer | Tests unitaires `canonical_paper_id`, dédup save_papers |
| `tests/test_paper_synthesizer.py` | Créer | Tests unitaires `parse_concepts_from_text`, `sanitize_paper_id`, batch request building |

---

## Task 1: corpus_collector.py — Canonical Paper ID (BS-1)

Ajouter `canonical_paper_id()` qui retourne `arxiv:{id}` OU `s2:{md5(title)[:16]}`. Mettre à jour la dédup et le frontmatter. Migrer automatiquement `seen-arxiv-ids.txt` → `seen-paper-ids.txt` au premier run.

**Files:**
- Modify: `corpus_collector.py`
- Create: `tests/test_corpus_collector.py`

- [ ] **Step 1: Installer les dépendances de test**

```bash
pip3 install pytest
```

Expected: `Successfully installed pytest-X.X.X` (ou "Requirement already satisfied")

- [ ] **Step 2: Créer tests/test_corpus_collector.py avec les tests qui doivent échouer**

```python
# tests/test_corpus_collector.py
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from corpus_collector import canonical_paper_id, normalize_arxiv_id


class TestCanonicalPaperId:
    def test_arxiv_paper_returns_prefixed_normalized_id(self):
        result = canonical_paper_id("2401.12345v2", "Some Title")
        assert result == "arxiv:2401.12345"

    def test_arxiv_paper_no_version_returns_prefixed_id(self):
        result = canonical_paper_id("2401.12345", "Some Title")
        assert result == "arxiv:2401.12345"

    def test_semantic_scholar_no_arxiv_returns_s2_hash(self):
        title = "Efficient IoT Edge Computing with Federated Learning"
        expected_hash = hashlib.md5(title.lower().strip().encode()).hexdigest()[:16]
        result = canonical_paper_id("", title)
        assert result == f"s2:{expected_hash}"

    def test_s2_hash_is_deterministic(self):
        title = "The Same Title"
        result1 = canonical_paper_id("", title)
        result2 = canonical_paper_id("", title)
        assert result1 == result2

    def test_s2_hash_case_insensitive(self):
        result_lower = canonical_paper_id("", "federated learning")
        result_upper = canonical_paper_id("", "Federated Learning")
        assert result_lower == result_upper

    def test_arxiv_takes_priority_over_title(self):
        result = canonical_paper_id("2401.99999", "Federated Learning")
        assert result.startswith("arxiv:")
        assert "s2:" not in result
```

- [ ] **Step 3: Vérifier que les tests échouent (`canonical_paper_id` n'existe pas encore)**

```bash
cd ~/Documents/Obsidian/KnowledgeBase && python3 -m pytest tests/test_corpus_collector.py -v
```

Expected: `ImportError: cannot import name 'canonical_paper_id'`

- [ ] **Step 4: Ajouter `import hashlib` en tête de corpus_collector.py**

Dans `corpus_collector.py`, après la ligne `import re` (ligne ~22) :

```python
import hashlib
```

- [ ] **Step 5: Ajouter la fonction `canonical_paper_id` après `normalize_arxiv_id`**

Dans `corpus_collector.py`, après la fonction `normalize_arxiv_id` (ligne ~68), insérer :

```python
def canonical_paper_id(arxiv_id: str, title: str) -> str:
    """Retourne une clé canonique stable pour la déduplication.

    - Paper arXiv : 'arxiv:{id_normalisé}'
    - Paper sans arXiv ID (Semantic Scholar, journals) : 's2:{md5(title)[:16]}'
    """
    if arxiv_id:
        return f"arxiv:{normalize_arxiv_id(arxiv_id)}"
    return f"s2:{hashlib.md5(title.lower().strip().encode()).hexdigest()[:16]}"
```

- [ ] **Step 6: Lancer les tests — ils doivent passer**

```bash
cd ~/Documents/Obsidian/KnowledgeBase && python3 -m pytest tests/test_corpus_collector.py -v
```

Expected: `6 passed`

- [ ] **Step 7: Mettre à jour `SEEN_IDS_FILE` pour pointer vers le nouveau fichier**

Dans `corpus_collector.py`, remplacer la ligne :
```python
SEEN_IDS_FILE = VAULT / "_logs/seen-arxiv-ids.txt"
```
par :
```python
SEEN_IDS_FILE = VAULT / "_logs/seen-paper-ids.txt"
```

- [ ] **Step 8: Mettre à jour `load_seen_ids` pour migrer l'ancien fichier**

Remplacer la fonction `load_seen_ids` existante :

```python
def load_seen_ids() -> set:
    """Charge les paper_ids déjà vus. Migre seen-arxiv-ids.txt si nécessaire."""
    legacy_file = SEEN_IDS_FILE.parent / "seen-arxiv-ids.txt"

    if not SEEN_IDS_FILE.exists() and legacy_file.exists():
        legacy_ids = {
            line.strip()
            for line in legacy_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        migrated = {f"arxiv:{id_}" for id_ in legacy_ids}
        SEEN_IDS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SEEN_IDS_FILE.write_text("\n".join(sorted(migrated)) + "\n", encoding="utf-8")
        print(f"[INFO] Migré {len(migrated)} IDs : seen-arxiv-ids.txt → seen-paper-ids.txt")
        return migrated

    if not SEEN_IDS_FILE.exists():
        return set()
    lines = SEEN_IDS_FILE.read_text(encoding="utf-8").splitlines()
    return {line.strip() for line in lines if line.strip()}
```

- [ ] **Step 9: Mettre à jour `save_papers` — dédup via `canonical_paper_id`, ajouter `paper_id` frontmatter**

Dans `save_papers()`, remplacer le bloc déduplication (les lignes `arxiv_id_raw = ...` jusqu'à `continue`) :

```python
        # ── Déduplication par canonical paper_id ────────────────────────────
        arxiv_id_raw = p.get("arxiv_id", "")
        paper_id = canonical_paper_id(arxiv_id_raw, p.get("title", ""))
        if paper_id in seen_ids:
            stats["duplicates"] += 1
            continue
```

Et dans le bloc "Marquer l'id comme vu" (remplacer les 3 dernières lignes du bloc save) :

```python
            # Enrichir le dict avec paper_id canonique
            p["paper_id"] = paper_id

            stats["saved"] += 1
            stats["scores"].append(score)
            seen_ids.add(paper_id)
```

- [ ] **Step 10: Ajouter `paper_id` dans `format_paper_as_markdown`**

Dans `format_paper_as_markdown()`, après la ligne `arxiv_id_norm = ...`, ajouter :

```python
    paper_id = paper.get("paper_id", canonical_paper_id(arxiv_id, paper.get("title", "")))
```

Et dans le bloc frontmatter retourné, après `arxiv_id_normalized:` ajouter la ligne :

```python
paper_id: "{paper_id}"
```

Le frontmatter doit ressembler à :
```yaml
---
type: paper
domain: {domain}
paper_id: "{paper_id}"
arxiv_id: "{arxiv_id}"
arxiv_id_normalized: "{arxiv_id_norm}"
```

- [ ] **Step 11: Test de non-régression — dry run corpus_collector**

```bash
cd ~/Documents/Obsidian/KnowledgeBase && python3 corpus_collector.py --domain ai --since 7 --max 2 --min-score 0.0
```

Expected: output sans erreur, `seen-paper-ids.txt` créé dans `_logs/` avec clés `arxiv:` préfixées.

- [ ] **Step 12: Vérifier la migration**

```bash
ls -la ~/Documents/Obsidian/KnowledgeBase/_logs/seen*.txt
head -5 ~/Documents/Obsidian/KnowledgeBase/_logs/seen-paper-ids.txt
```

Expected: `seen-paper-ids.txt` existe avec lignes de la forme `arxiv:2401.12345`

- [ ] **Step 13: Commit**

```bash
cd ~/Documents/Obsidian/KnowledgeBase
git add corpus_collector.py tests/test_corpus_collector.py
git commit -m "fix(corpus): canonical paper_id — dédup Semantic Scholar sans ArXiv ID (BS-1)"
```

---

## Task 2: nightly-agent.sh — Flock Concurrent Guard (BS-2)

Ajouter un verrou `flock` en tout début de script pour empêcher deux instances concurrentes. Le guard date existant est conservé comme check secondaire.

**Files:**
- Modify: `nightly-agent.sh`

- [ ] **Step 1: Vérifier que flock est disponible sur macOS**

```bash
which flock || echo "absent"
```

Si absent : `brew install util-linux` (flock est dans util-linux sur macOS).

Expected: `/usr/local/bin/flock` ou `/opt/homebrew/bin/flock`

- [ ] **Step 2: Ajouter le flock guard au début du script**

Dans `nightly-agent.sh`, après la ligne `set -euo pipefail` et AVANT toutes les variables, insérer :

```bash
# ── Concurrent guard (flock) ─────────────────────────────────────────────────
# Empêche deux instances simultanées (ex: launchd retry pendant un run long).
# flock -n échoue immédiatement si le verrou est déjà acquis.
LOCKFILE="${HOME}/Documents/Obsidian/KnowledgeBase/_logs/nightly.lock"
exec 200>"$LOCKFILE"
flock -n 200 || {
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Nightly already running (lock held) — skip" \
    >> "${HOME}/Documents/Obsidian/KnowledgeBase/_logs/nightly-agent.log"
  exit 0
}
trap "flock -u 200" EXIT
```

Le résultat en tête de fichier doit être :

```bash
#!/bin/bash
# nightly-agent.sh — Agent nocturne Second Brain (Light Mode)
# ...
set -euo pipefail

# ── Concurrent guard (flock) ─────────────────────────────────────────────────
LOCKFILE="${HOME}/Documents/Obsidian/KnowledgeBase/_logs/nightly.lock"
exec 200>"$LOCKFILE"
flock -n 200 || {
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Nightly already running (lock held) — skip" \
    >> "${HOME}/Documents/Obsidian/KnowledgeBase/_logs/nightly-agent.log"
  exit 0
}
trap "flock -u 200" EXIT

VAULT="$HOME/Documents/Obsidian/KnowledgeBase"
# ... reste du script
```

- [ ] **Step 3: Tester le concurrent guard manuellement**

```bash
# Terminal 1 — simuler un run long (sleep 10 = process qui tient le lock)
exec 200>"${HOME}/Documents/Obsidian/KnowledgeBase/_logs/nightly.lock"
flock 200
sleep 10 &
HOLD_PID=$!

# Terminal 2 — lancer le script → doit skip immédiatement
bash ~/Documents/Obsidian/KnowledgeBase/nightly-agent.sh &
sleep 1
grep "already running" ~/Documents/Obsidian/KnowledgeBase/_logs/nightly-agent.log | tail -1

# Cleanup Terminal 1
kill $HOLD_PID 2>/dev/null; flock -u 200
```

Expected: ligne `already running (lock held)` dans le log.

- [ ] **Step 4: Commit**

```bash
cd ~/Documents/Obsidian/KnowledgeBase
git add nightly-agent.sh
git commit -m "fix(nightly): flock concurrent guard — empêche 2 instances simultanées (BS-2)"
```

---

## Task 3: paper_synthesizer.py — Migration Gemini → Claude Haiku Batch

Remplacer l'API Gemini (bloquée EU) par l'Anthropic Messages Batches API. Ajouter `cache_control` sur le system prompt. Nommer les fichiers de sortie `A-{paper_id_sanitized}-{n}.md`. Ajouter recovery via `_logs/batch_jobs.json`.

**Files:**
- Modify: `paper_synthesizer.py`
- Create: `tests/test_paper_synthesizer.py`

- [ ] **Step 1: Installer l'Anthropic SDK**

```bash
pip3 install anthropic
```

Expected: `Successfully installed anthropic-X.X.X`

- [ ] **Step 2: Créer tests/test_paper_synthesizer.py avec les tests qui doivent passer**

```python
# tests/test_paper_synthesizer.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from paper_synthesizer import parse_concepts_from_text, sanitize_paper_id


class TestSanitizePaperId:
    def test_arxiv_id_replaces_colon_and_dot(self):
        assert sanitize_paper_id("arxiv:2401.12345") == "arxiv-2401-12345"

    def test_s2_id_replaces_colon(self):
        assert sanitize_paper_id("s2:abc1234567890abc") == "s2-abc1234567890abc"

    def test_no_special_chars_unchanged(self):
        assert sanitize_paper_id("arxiv-2401-12345") == "arxiv-2401-12345"


class TestParseConceptsFromText:
    def test_parses_single_valid_concept(self):
        text = '''
{"concept_title": "Le federated learning réduit la transmission de données de 60%",
 "tier": "S",
 "tier_reason": "Applicable à second-brain pour sync offline",
 "essence": "Entraîner localement, partager uniquement les gradients.",
 "detail": "Détail complet ici.",
 "tags": ["ml", "privacy"],
 "simple_explanation": "Apprendre sans envoyer ses données.",
 "paper_id": "arxiv:2401.12345",
 "source_url": "https://arxiv.org/abs/2401.12345"}
'''
        concepts = parse_concepts_from_text(text)
        assert len(concepts) == 1
        assert concepts[0]["tier"] == "S"
        assert concepts[0]["concept_title"].startswith("Le federated")

    def test_parses_multiple_concepts(self):
        text = '''
{"concept_title": "Concept A", "tier": "S", "essence": "E1",
 "tier_reason": "r", "detail": "d", "tags": [], "simple_explanation": "s",
 "paper_id": "arxiv:1", "source_url": "http://a"}

{"concept_title": "Concept B", "tier": "A", "essence": "E2",
 "tier_reason": "r", "detail": "d", "tags": [], "simple_explanation": "s",
 "paper_id": "arxiv:1", "source_url": "http://a"}
'''
        concepts = parse_concepts_from_text(text)
        assert len(concepts) == 2

    def test_ignores_invalid_json(self):
        text = 'Some prose {"broken": json, } more prose'
        concepts = parse_concepts_from_text(text)
        assert len(concepts) == 0

    def test_ignores_json_missing_required_keys(self):
        text = '{"title": "No concept_title key", "tier": "S"}'
        concepts = parse_concepts_from_text(text)
        assert len(concepts) == 0

    def test_filters_by_min_tier(self):
        text = '''
{"concept_title": "Tier S concept", "tier": "S", "essence": "E",
 "tier_reason": "r", "detail": "d", "tags": [], "simple_explanation": "s",
 "paper_id": "p", "source_url": "u"}
{"concept_title": "Tier B concept", "tier": "B", "essence": "E",
 "tier_reason": "r", "detail": "d", "tags": [], "simple_explanation": "s",
 "paper_id": "p", "source_url": "u"}
'''
        all_concepts = parse_concepts_from_text(text)
        assert len(all_concepts) == 2
        # Filtrage par tier fait en amont — parse retourne tout
        tier_s = [c for c in all_concepts if c["tier"] == "S"]
        assert len(tier_s) == 1
```

- [ ] **Step 3: Lancer les tests — `sanitize_paper_id` doit échouer (pas encore implémentée)**

```bash
cd ~/Documents/Obsidian/KnowledgeBase && python3 -m pytest tests/test_paper_synthesizer.py -v
```

Expected: `ImportError: cannot import name 'sanitize_paper_id'` (ou des failures sur ce test)

- [ ] **Step 4: Remplacer les imports Gemini par Anthropic en tête de paper_synthesizer.py**

Remplacer :
```python
from google import genai
from google.genai import types as genai_types
```

Par :
```python
import anthropic
from collections import defaultdict
```

- [ ] **Step 5: Mettre à jour les constantes**

Remplacer :
```python
MODEL = "gemini-2.0-flash"
MAX_TOKENS_CONCEPTS = 1024
MAX_TOKENS_DIGEST = 1500
GEMINI_RATE_LIMIT_DELAY = 4.0  # secondes entre appels (15 RPM max)

# Gemini model instance (configured in main after API key check)
model = None  # genai.Client, set in main()
```

Par :
```python
MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS_CONCEPTS = 1024
MAX_TOKENS_DIGEST = 1500

BATCH_JOBS_FILE = LOGS_DIR / "batch_jobs.json"
```

- [ ] **Step 6: Remplacer CONCEPT_EXTRACTION_PROMPT par un SYSTEM_PROMPT cacheable et un USER_PROMPT**

Remplacer le bloc `CONCEPT_EXTRACTION_PROMPT = """..."""` entier par :

```python
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
```

- [ ] **Step 7: Ajouter la fonction `sanitize_paper_id` après les constantes**

```python
def sanitize_paper_id(paper_id: str) -> str:
    """Transforme un paper_id en segment de nom de fichier sûr.

    'arxiv:2401.12345' → 'arxiv-2401-12345'
    's2:abc123'        → 's2-abc123'
    """
    return paper_id.replace(":", "-").replace(".", "-")
```

- [ ] **Step 8: Lancer les tests — ils doivent maintenant tous passer**

```bash
cd ~/Documents/Obsidian/KnowledgeBase && python3 -m pytest tests/test_paper_synthesizer.py -v
```

Expected: `8 passed`

- [ ] **Step 9: Mettre à jour `write_concept_note` — nouveau naming `A-{paper_id_sanitized}-{n}.md`**

Remplacer la signature et les premières lignes de `write_concept_note` :

```python
def write_concept_note(concept: dict, domain: str, week_num: int, today: str,
                       index: int = 1) -> Path:
    """Write a pre-note atomic file to _inbox/raw/concepts/. Returns the path.

    Naming convention : A-{paper_id_sanitized}-{n}.md
    Ex: A-arxiv-2401-12345-1.md, A-s2-abc1234567890abc-2.md
    """
    CONCEPTS_DIR.mkdir(parents=True, exist_ok=True)

    paper_id = concept.get("paper_id", "")
    pid_sanitized = sanitize_paper_id(paper_id) if paper_id else slugify(concept.get("concept_title", "untitled"))
    out_path = CONCEPTS_DIR / f"A-{pid_sanitized}-{index}.md"
```

Le reste de la fonction (construction du contenu) reste identique.

- [ ] **Step 10: Ajouter les fonctions de gestion du batch**

Ajouter après `write_concept_note` et avant `write_digest` :

```python
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


def load_pending_batch_job(domain: str) -> str | None:
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

def submit_batch(papers: list[dict], client: anthropic.Anthropic) -> str:
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
                   poll_interval: int = 15) -> None:
    """Poll jusqu'à ce que le batch soit terminé."""
    print(f"  [INFO] Batch {batch_id} soumis, polling…", file=sys.stderr)
    while True:
        status = client.messages.batches.retrieve(batch_id)
        if status.processing_status == "ended":
            return
        counts = status.request_counts
        print(
            f"  [INFO] Batch {batch_id} — processing: {counts.processing} "
            f"succeeded: {counts.succeeded} errored: {counts.errored}",
            file=sys.stderr,
        )
        time.sleep(poll_interval)
```

- [ ] **Step 11: Réécrire `process_domain` pour utiliser le Batch API**

Remplacer toute la fonction `process_domain` :

```python
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

        raw_text = result.result.message.content[0].text
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
    # Grouper par paper_id pour assigner l'index de concept
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
```

- [ ] **Step 12: Mettre à jour `main()` — remplacer init Gemini par Anthropic**

Trouver le bloc `main()` et remplacer toute vérification de `GOOGLE_API_KEY` et `model = genai.Client(...)` par :

```python
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
```

- [ ] **Step 13: Mettre à jour `write_metrics` — remplacer référence Gemini et agréger les erreurs**

Dans `write_metrics()`, après les lignes qui calculent `tier_dist`, ajouter :
```python
    all_errors = []
    for m in metrics_list:
        all_errors.extend(m.get("errors", []))
```

Et remplacer :
```python
    # Rough token estimate (for informational purposes only — Gemini free tier has no cost)
    estimated_tokens = concepts_total * MAX_TOKENS_CONCEPTS + digests_total * MAX_TOKENS_DIGEST
```
Par :
```python
    # Estimate tokens (Claude Haiku Batch ~$0.40/MTok input, $2/MTok output)
    estimated_tokens = concepts_total * MAX_TOKENS_CONCEPTS + digests_total * MAX_TOKENS_DIGEST
```

Dans l'objet JSON final écrit par `write_metrics`, s'assurer que le champ `errors` utilise `all_errors` à la place de `[]` ou de toute valeur fixe.

- [ ] **Step 14: Dry-run test pour vérifier que le script démarre sans erreur**

```bash
cd ~/Documents/Obsidian/KnowledgeBase && python3 paper_synthesizer.py --dry-run --domain ai
```

Expected: affiche la liste des papers sans appeler l'API, pas d'erreur Python.

- [ ] **Step 15: Lancer tous les tests**

```bash
cd ~/Documents/Obsidian/KnowledgeBase && python3 -m pytest tests/ -v
```

Expected: `14 passed` (6 corpus_collector + 8 paper_synthesizer)

- [ ] **Step 16: Commit**

```bash
cd ~/Documents/Obsidian/KnowledgeBase
git add paper_synthesizer.py tests/test_paper_synthesizer.py
git commit -m "feat(synthesizer): migrate Gemini EU-bloqué → Claude Haiku Batch + cache_control (F22)"
```

---

## Task 4: .nightly-prompt.md — Overflow Drain + Ceiling + Bootstrap (BS-4, BS-5, F9)

Quatre modifications chirurgicales au prompt :
1. **Étape 0** : ajouter ceiling guard (note_count ≥ 285), fleeting guard (≥ 15), overflow FIFO drain, batch_job_id check
2. **Étape 2A** : mettre à jour le glob `draft-*.md` → `A-*.md`  
3. **Étape 3** : ajouter bootstrap mode (vault_notes < 50 → pas de filtre recency)
4. **Étape 5** : ajouter INDEX diff (mise à jour uniquement des notes modifiées depuis `last_run`)

**Files:**
- Modify: `.nightly-prompt.md`

- [ ] **Step 1: Remplacer le bloc "Guard pre-run" de l'Étape 0**

Trouver le bloc actuel :
```markdown
**Guard pre-run :**
1. Compter les fichiers dans `_inbox/` (hors `_processed/`)
2. Lire `_logs/last-nightly.json` → extraire `last_lint_date`
3. Si inbox vide ET lint effectué il y a moins de 3 jours → écrire dans `_logs/last-nightly.json` :
   ```json
   {"status": "skipped", "reason": "no work", "last_run": "TIMESTAMP_ISO"}
   ```
   Puis **arrêter le run immédiatement**.

Écrire `_logs/last-nightly.json` (si run non skippé) :
```json
{"status": "in_progress", "started": "TIMESTAMP_ISO", "notes_added": 0, "errors": []}
```
```

Remplacer par :
```markdown
**Guard pre-run (dans l'ordre — tout fail bloquant → abort + log) :**

1. **Ceiling guard** : compter les notes vault dans `universal/`, `projects/` (hors `_processed/`, `_inbox/`).
   - Si `note_count ≥ 285` → écrire `_inbox/review/review-required.md` avec :
     ```markdown
     # Vault Ceiling Alert — YYYY-MM-DD
     note_count a atteint {note_count}/300 — review manuelle requise avant ajout de nouvelles notes.
     ```
     Puis **arrêter le run**.
   - Si `note_count ≥ 250` → logger un warning dans `_logs/last-nightly.json`, continuer.

2. **Fleeting guard** : compter les notes avec `maturity: fleeting`.
   - Si `fleeting_count ≥ 15` → écrire `_inbox/review/vault-health-alert.md` :
     ```markdown
     # Vault Health Alert — YYYY-MM-DD
     {fleeting_count} notes fleeting non reviewées — synthèse suspendue, lint seul.
     ```
     Passer directement à l'Étape 4 (lint uniquement).

3. **batch_job_id check** : si `_logs/batch_jobs.json` contient des entrées sans fichiers `A-*.md` correspondants dans `_inbox/raw/concepts/` → logger un warning dans `_logs/last-nightly.json`, continuer.

4. **Overflow drain** : si `_inbox/overflow/` contient des fichiers → prendre les `min(count, 5)` plus anciens (FIFO) et les déplacer vers `_inbox/raw/concepts/` ou `_inbox/raw/articles/` selon leur type (`type` dans le frontmatter). Ces fichiers comptent dans le cap de 15 de l'Étape 2.

5. **Inbox check** : compter les fichiers dans `_inbox/` (hors `_processed/`, `overflow/`).
   - Si inbox vide ET lint effectué il y a moins de 3 jours → écrire dans `_logs/last-nightly.json` :
     ```json
     {"status": "skipped", "reason": "no work", "last_run": "TIMESTAMP_ISO"}
     ```
     Puis **arrêter le run**.

Écrire `_logs/last-nightly.json` (si run non skippé) :
```json
{"status": "in_progress", "started": "TIMESTAMP_ISO", "notes_added": 0, "errors": []}
```
```

- [ ] **Step 2: Mettre à jour Étape 2A — glob `draft-*.md` → `A-*.md` et supprimer l'étape de renommage**

Trouver dans `#### 2A — _inbox/raw/concepts/` :
```markdown
Ces fichiers ont déjà été synthétisés par paper_synthesizer.py. NE PAS re-synthétiser.

Pour chaque fichier `draft-*.md` dans `_inbox/raw/concepts/` :
```

Remplacer la ligne de glob et les étapes 6-7 :

```markdown
Ces fichiers ont déjà été synthétisés par paper_synthesizer.py. NE PAS re-synthétiser.
Naming convention : `A-{paper_id_sanitized}-{n}.md` (ex: `A-arxiv-2401-12345-1.md`).
Cap : **15 fichiers max par run** incluant les fichiers overflow déjà drainés en Étape 0.

Pour chaque fichier `A-*.md` dans `_inbox/raw/concepts/` (FIFO — traiter les plus anciens en premier) :
1. Chercher le nom dans `_meta/LOG.md` — si trouvé → skip
2. Lire le contenu
3. **Valider** le frontmatter YAML : vérifier que `type`, `tier`, `source_chain`, `paper_id` sont présents et valides
4. **Valider** le titre : est-ce une phrase affirmative testable ? Si non → corriger selon la règle titre obligatoire
5. Déterminer la destination selon l'arbre filing (VAULT.md) : `universal/` ou `projects/<projet>/`
6. Déplacer le fichier vers sa destination (le nom `A-{paper_id_sanitized}-{n}.md` est conservé)
7. Appender dans `_meta/LOG.md` : `## [YYYY-MM-DD] ingest | raw/concepts/A-xxx.md → 1 note (synthesizer)`
8. Déplacer source originale vers `_inbox/raw/concepts/_processed/YYYY-MM-DD-A-xxx.md`

Si > 15 fichiers dans `_inbox/raw/concepts/` → traiter les 15 premiers (FIFO), déplacer le reste vers `_inbox/overflow/`.
```

- [ ] **Step 3: Ajouter le bootstrap mode à l'Étape 3**

Dans `### Étape 3 — Cross-références`, après la ligne `Budget : max **10 notes existantes mises à jour par run** total`, ajouter :

```markdown
**Bootstrap mode (vault_notes < 50) :**
Si le nombre total de notes vault est inférieur à 50 (vault en phase d'initialisation), désactiver le filtre tag et utiliser TOUTES les notes vault comme candidates pour les cross-refs (le set est suffisamment petit pour un scan complet). Maintenir le budget de 10 notes mises à jour max.
```

- [ ] **Step 4: Ajouter l'INDEX diff à l'Étape 5**

Dans `### Étape 5 — Régénérer INDEX.md + context-cards + MOC`, après la section `**INDEX.md structuré :**`, ajouter une note avant le bloc template :

```markdown
**INDEX diff (optimisation budget) :**
Lire `_logs/last-nightly.json` → extraire `last_run` (timestamp). Pour la mise à jour de l'INDEX, reconstruire uniquement les entrées des notes dont la date `created` ou le frontmatter a été modifié depuis `last_run`. Les notes non modifiées conservent leur entrée existante dans l'INDEX. Si `last_run` est absent ou si plus de 20 notes ont été ajoutées depuis le dernier run → reconstruire l'INDEX complet.
```

- [ ] **Step 5: Vérifier que le prompt est syntaxiquement valide (pas de markdown cassé)**

```bash
# Vérifier les titres de sections (doit lister tous les ### Étape 0-6)
grep "^### Étape" ~/Documents/Obsidian/KnowledgeBase/.nightly-prompt.md
```

Expected: 7 lignes `### Étape 0` à `### Étape 6`

- [ ] **Step 6: Commit**

```bash
cd ~/Documents/Obsidian/KnowledgeBase
git add .nightly-prompt.md
git commit -m "feat(nightly-prompt): ceiling guard + overflow drain + A-*.md glob + bootstrap cross-refs + INDEX diff (BS-4, BS-5, F9)"
```

---

## Task 5: Validation End-to-End Sprint 1

Vérifier que le pipeline complet tourne sans erreur avec les 4 fixes en place.

**Files:** aucun fichier modifié — validation seule.

- [ ] **Step 1: Lancer la suite de tests complète**

```bash
cd ~/Documents/Obsidian/KnowledgeBase && python3 -m pytest tests/ -v
```

Expected: `14 passed, 0 failed`

- [ ] **Step 2: Dry-run paper_synthesizer sur tous les domaines**

```bash
export ANTHROPIC_API_KEY="sk-ant-..."  # remplacer par la vraie clé
cd ~/Documents/Obsidian/KnowledgeBase && python3 paper_synthesizer.py --dry-run
```

Expected: liste des papers par domaine, `0 errors`

- [ ] **Step 3: Dry-run corpus_collector**

```bash
cd ~/Documents/Obsidian/KnowledgeBase && python3 corpus_collector.py --domain ai --since 3 --max 2
```

Expected: résultats affichés, `seen-paper-ids.txt` mis à jour avec clés `arxiv:` ou `s2:`

- [ ] **Step 4: Vérifier la structure du vault**

```bash
ls ~/Documents/Obsidian/KnowledgeBase/_logs/
ls ~/Documents/Obsidian/KnowledgeBase/_inbox/
```

Expected:
- `_logs/seen-paper-ids.txt` présent
- `_logs/seen-arxiv-ids.txt` toujours présent (ne pas supprimer — référence historique)
- Pas de `_logs/nightly.lock` résiduel (supprimé par trap EXIT)

- [ ] **Step 5: Commit final Sprint 1 + tag**

```bash
cd ~/Documents/Obsidian/KnowledgeBase
git tag sprint1-complete
git log --oneline -5
```

Expected: 4 commits depuis la baseline, tag `sprint1-complete`

---

## Résultat Sprint 1

Après ces 4 tâches :
- ✓ corpus_collector.py déduplique correctement les 45+ papers Semantic Scholar en backlog
- ✓ nightly-agent.sh ne peut plus lancer deux instances simultanées
- ✓ paper_synthesizer.py tourne avec Claude Haiku Batch (~$0.06/semaine, EU-safe)
- ✓ Les 51 papers en backlog peuvent être traités via `python3 paper_synthesizer.py`
- ✓ .nightly-prompt.md gère overflow, ceiling, et cross-refs bootstrap

**Sprint 2** (Track B — NotebookLM MCP) peut commencer une fois Sprint 1 validé. Voir la spec §11.

---

## Notes d'implémentation

- `ANTHROPIC_API_KEY` doit être définie en env var. Ajouter dans `~/.zshrc` : `export ANTHROPIC_API_KEY="sk-ant-..."`
- `flock` sur macOS nécessite `brew install util-linux` si absent
- Les tests unitaires ne font pas d'appels API réels — aucune clé nécessaire pour les lancer
- `seen-arxiv-ids.txt` est conservé après migration (ne pas supprimer — référence historique si besoin de debug)
- Le Batch API poll toutes les 15 secondes. Pour 15 papers, prévoir ~2-5 min de traitement.
