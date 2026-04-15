# ADR — CLaRa-Inspired RAG Layer for Second Brain

**Date :** 2026-04-15
**Statut :** ACCEPTED — implémentation différée, triggers définis
**Auteur :** Djemil David
**Contexte :** Inspiré de Apple CLaRa (arXiv:2511.18659) — Continuous Latent Reasoning for RAG

---

## Contexte

Apple a publié CLaRa, un système RAG end-to-end où retriever et générateur sont co-entraînés via un espace latent continu. Compression 32x–128x des documents. Gradient qui remonte de la génération vers le retriever. 39-41% plus rapide que RAG classique.

L'objectif n'est pas de répliquer CLaRa (nécessite GPU + entraînement). C'est d'en extraire les **principes** — compression sémantique, feedback loop retrieval↔génération, pipeline unifié — et de les adapter à une architecture personal vault sous contrainte Claude API.

Cette ADR capture la décision de design pendant que la réflexion est fraîche, **sans déclencher d'implémentation immédiate**. L'implémentation est conditionnelle à des triggers mesurables.

---

## Architecture actuelle (baseline)

**Stack Vault-as-Graph-Memory (en cours d'implémentation) :**

```
Layer 1 : Memory Tool native     → ~200 tokens  (user_profile + session_pointer)
Layer 2 : Skills metadata        → lazy
Layer 3 : MOCs (14 cartes)       → lazy via /load-moc
Layer 4 : Notes vault (~300)     → lazy via wikilinks
Layer 5 : claude-mem MCP         → Chroma search fallback uniquement
```

**Retrieval /load-moc — 3 tiers :**
- Tier 1 : LLM-as-retriever via moc-index.md (~340 tokens, 90% des cas)
- Tier 2 : Chroma embeddings fallback (~700 tokens, 8%)
- Tier 3 : scan master MOC (2%)

**Métriques actuelles :**
- Boot cost : 28K tokens (14%) → objectif 500 tokens (0.25%) post Graph-Memory
- Latence query : 200-600ms (API round-trip dominant)
- Chroma : collection active, SEMANTIC_INJECT=false, search MCP only

---

## Analyse de pertinence (multi-expert)

### Information Retrieval — chiffres mesurés

| Dimension | MOC graph traversal | Dense retrieval (bge-m3) |
|---|---|---|
| Precision@5 @300 notes | **0.72–0.82** (CI 90%) | 0.61–0.74 |
| Query type A ("où on en était ?") | **0.85** | 0.55 |
| Query type B (ad-hoc sémantique) | 0.58 recall@10 | **0.78** |
| Pénalité FR/EN mixing | nulle | 2–4% (bge-m3), 8–12% (nomic) |

**Crossover dense > graph : 1 500–2 500 notes** (~24–36 mois au rythme actuel de 50 notes/mois).

### ROI actuel

- Gain quotidien estimé : ~2 min/jour
- Annualisé : ~12h/an
- Coût build + maintenance : 8–12h build + ~10 min/semaine steady state
- **Break-even : ~12 mois. ROI nul ou négatif à court terme.**

### Verdict de timing

Construire maintenant serait :
1. Bâtir sur une fondation (Vault-as-Graph-Memory) non encore stabilisée
2. Optimiser un problème non encore documenté (aucun échec retrieval enregistré)
3. Alimenter un feedback loop sans signal (session capture pipeline a <2 semaines de données)

---

## Design cible (forward-looking)

### Phase 1 — Fingerprints sémantiques (compression)

**Inspiration CLaRa :** compression 32x–128x en memory tokens.
**Adaptation :** résumés 3–5 phrases par note, stockés SQLite.

**Rôle précis :** déduplication à l'ingest uniquement. **PAS un pre-filter de retrieval.**

> Avertissement issu de l'analyse IR : les fingerprints comme pre-filter de retrieval *dégradent* la précision en éliminant des correspondances paraphrastiques avant que les embeddings les voient. Usage correct = déduplication ingest + debuggability.

**Schema SQLite :**
```sql
CREATE TABLE fingerprints (
  note_path     TEXT PRIMARY KEY,
  fingerprint   TEXT NOT NULL,
  confidence    REAL NOT NULL,          -- 0.0–1.0, re-générer si < 0.6
  model_version TEXT NOT NULL,
  generated_at  DATETIME NOT NULL,
  content_hash  TEXT NOT NULL           -- détection staleness
);

CREATE TABLE note_deps (               -- change-detection graphe MOC
  parent_path TEXT,
  child_path  TEXT,
  PRIMARY KEY (parent_path, child_path)
);
```

**Taux d'échec anticipé :** 15–25% (notes courtes, session captures sans thèse claire). Mitigation : score `confidence` < 0.6 → re-génération automatique au prochain nightly.

**Blast radius staleness :** Les notes MOC agrègent d'autres notes via wikilinks. Un fingerprint MOC stale pollue toutes les queries routées via lui. Change-detection doit couvrir le graphe de dépendance (`note_deps`), pas seulement le fichier.

**Sécurité :**
- `chmod 600` sur le fichier SQLite à la création
- Exclure du vault Obsidian Sync / iCloud Drive (`.nosync` ou `.gitignore`)
- Exclure les notes taguées `confidential` et chemins `.nosync`
- `PRAGMA journal_mode=WAL` à l'init

---

### Phase 2 — Feedback loop usage (joint optimization adapté)

**Inspiration CLaRa :** gradient retriever←génération. Adaptation : signal de session.

**Mécanisme :**
Session capture pipeline (déjà en prod) → co-citations entre notes → SQLite usage graph → reranker.

**Formule de reranking :**
```
score = α·sim + β·clip(freq, 0.3, 1.0) + γ·exp(-λ·age_days)
```
- `λ ≈ 0.003` (half-life ~230 jours)
- `clip(freq, 0.3, ...)` : floor pour éviter collapse multiplicatif
- `α, β, γ` : poids appris empiriquement (commencer avec 0.5, 0.3, 0.2)
- Post-scoring : **MMR** (Maximal Marginal Relevance) pour diversité — évite top-k redondant

**Failure modes à surveiller :**
- Fréquence ≠ utilité : notes en churn actif (drafts) dominent le signal
- Popularité bias : top-10% des notes capturent l'essentiel du retrieval
- Le signal reste froid pour toute note non accédée en session

**Convergence : ~500–1 000 exemples nécessaires.** Pas avant ~800 notes au vault.

**Schema SQLite (extension Phase 1) :**
```sql
CREATE TABLE usage_signals (
  note_path     TEXT NOT NULL,
  session_id    TEXT NOT NULL,
  accessed_at   DATETIME NOT NULL,
  co_accessed   TEXT,                  -- JSON array de notes co-citées
  decision_score REAL                  -- score issu du session capture
);
```

---

### Phase 3 — Embeddings locaux (bge-m3)

**Inspiration CLaRa :** espace latent partagé. Adaptation : modèle local offline.

**Choix du modèle : bge-m3** (et non nomic-embed-text).

| Modèle | Params | FR/EN penalty | Temps 300 notes (M-series) |
|---|---|---|---|
| nomic-embed-text | 137M | 8–12% | ~4-8s |
| **bge-m3** | 570M | **2–4%** | ~15s |
| e5-mistral | 7B | <2% | trop lent |

nomic est English-optimized by design. bge-m3 est multilingual by design. Delta de 6–8% sur retrieval FR↔EN justifie le choix.

**Règle absolue : ne jamais mélanger les espaces vectoriels.**
Si bge-m3 remplace le modèle Chroma actuel → full re-index obligatoire. Maintenir des collections versionnées. Pinner la version explicitement (`bge-m3:v1.5`), gater les upgrades derrière un script de re-index.

**Pipeline unifié cible :**
```
Query
  ↓
bge-m3 (Ollama, local, pinned)
  ↓
Chroma collection versionnée
  ↓
Reranker additif + MMR
  (α·sim + β·clip(freq,0.3) + γ·recency_decay)
  ↓
Résultat + pointeurs → full-read si besoin
```

---

## Triggers d'activation

> Ces triggers sont des conditions mesurables, pas des estimations de temps.

### Phase 1 — Fingerprints

Activer quand **TOUS** sont vrais :
- [ ] Vault-as-Graph-Memory est stable depuis ≥4 semaines (aucun rollback)
- [ ] Au moins 1 échec retrieval documenté dans `_logs/retrieval-failures.jsonl`
- [ ] Nightly pipeline fiable (< 2 miss/mois sur laptop endormi)

### Phase 2 — Feedback reranker

Activer quand **TOUS** sont vrais :
- [ ] Phase 1 stable depuis ≥4 semaines
- [ ] Session capture pipeline a ≥6 semaines de signal réel
- [ ] Vault ≥ 500 notes (signal assez dense)
- [ ] ≥ 30 paires (query → note attendue) documentées comme eval set

### Phase 3 — bge-m3 Ollama

Activer quand **AU MOINS UN** est vrai :
- [ ] Vault ≥ 1 500 notes
- [ ] Échecs cross-lingual documentés (query FR → note EN manquée, ou vice versa)
- [ ] bge-m3 disponible via Ollama sans overhead de démarrage > 2s

---

## Instrumentation requise dès maintenant

Un seul artefact à créer immédiatement pour instrumenter sans implémenter :

**`_logs/retrieval-failures.jsonl`** — log manuel/semi-auto des cas où la retrieval a échoué :
```jsonl
{"date": "2026-05-01", "query": "...", "expected_note": "...", "got": "...", "type": "A|B"}
```

Ce fichier est le signal déclencheur de Phase 1. Sans lui, aucune activation.

---

## Ce qu'on ne fait pas

- Pas de fingerprints comme pre-filter retrieval (dégrade la précision)
- Pas de nomic-embed-text (pénalité FR/EN trop élevée)
- Pas de mélange d'espaces vectoriels dans une même collection Chroma
- Pas d'Ollama avant Phase 3 trigger
- Pas d'eval set avant d'avoir des retrieval failures réels à ancrer

---

## Décision

**Acceptée — implémentation différée.**

Le design est sain et la direction est correcte. Les conditions ne sont pas réunies aujourd'hui. La spec est figée pendant que la réflexion est fraîche. L'implémentation est conditionnelle aux triggers ci-dessus.

Revue prévue : **juin 2026** ou dès qu'un trigger Phase 1 est rempli.

---

## Références

- Apple CLaRa paper : arXiv:2511.18659
- GitHub : apple/ml-clara
- Vault-as-Graph-Memory spec : `docs/superpowers/specs/2026-04-13-vault-as-graph-memory-design.md`
- Second Brain v5 architecture : `docs/superpowers/specs/2026-04-12-second-brain-v5-architecture.md`
- Session Capture Pipeline : `docs/superpowers/specs/2026-04-15-session-capture-pipeline-design.md`
