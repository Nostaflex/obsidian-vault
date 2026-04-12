# Spec — Pipeline de Synthèse Hybride Claude × NotebookLM
**Version :** 1.0  
**Date :** 2026-04-12  
**Statut :** Validé — prêt pour implémentation  
**Auteur :** Djemil David (architecture), Claude Sonnet 4.6 + Opus 4.6 (review)

---

## 1. Contexte et Objectifs

### Problème résolu

`paper_synthesizer.py` est bloqué : l'API Gemini free tier retourne `limit: 0` en France (EU/EEA). 51 papers attendent en queue dans `_inbox/raw/papers/`. Le nightly agent ne peut pas remplir son rôle faute d'input de synthèse.

### Objectifs du système

| Objectif | Description |
|----------|-------------|
| **Débloquer la synthèse** | Migrer paper_synthesizer.py de Gemini vers Claude Haiku via Anthropic Batch API — EU-safe, ~$0.001/run |
| **Enrichissement grounded** | Ajouter NotebookLM comme couche de vérification et découverte cross-domaines via browser automation MCP |
| **Architecture résiliente** | NLM enrichit mais ne gate jamais. Si NLM tombe → Claude seul suffit pour un run complet |
| **Qualité vault intacte** | Tous les invariants PKM (Mitose Cognitive, Anti-Collector's Fallacy, titres déclaratifs) sont enforced par design |

### Décision d'architecture

**Approche B — Dual-Track Séquentiel** : Track A (Claude Haiku Batch) s'exécute en premier et produit un output complet. Track B (NotebookLM MCP) enrichit l'output de Track A. Si Track B échoue → circuit breaker, Track A seul est filé au nightly agent. Les 4 patterns d'hybridation sont couverts en automatique.

---

## 2. Vue d'Ensemble du Pipeline

```
SAMEDI
  corpus_collector.py
    ↓ arXiv + Semantic Scholar (scoring S/A/B/C, dedup paper_id)
  _inbox/raw/papers/{ai|iot|cloud|ecommerce}/

DIMANCHE (séquentiel, deadline 23h30)
  ┌─────────────────────────────────────────────┐
  │  TRACK A — Claude Haiku (PRIMARY)           │
  │  paper_synthesizer.py                       │
  │  Anthropic Batch API + cache_control        │
  │  Output: A-{paper_id}.md (idempotent)       │
  └─────────────────┬───────────────────────────┘
                    ↓ (Track A complet avant Track B)
  ┌─────────────────────────────────────────────┐
  │  TRACK B — NotebookLM MCP (ENRICHISSEMENT)  │
  │  m4yk3ldev (forké, pinné, compte dédié)     │
  │  Abstract only · rotation @45 sources       │
  │  Output: B-{paper_id}-grounded.md           │
  │  Circuit breaker: skip si auth fail         │
  └─────────────────────────────────────────────┘

QUOTIDIEN 2h17 (nightly agent v5+)
  Guard → Intake A+B → Cross-refs → Lint → INDEX diff → Health

ON-DEMAND
  notebook_query → Q&A grounded → bridge notes
```

---

## 3. Spécification des Composants

### 3.1 corpus_collector.py — Fix Dédup Semantic Scholar

**Problème identifié (BS-1) :** Les papers sans ArXiv ID (conference proceedings, journals) ont `arxiv_id = ""`. La condition `if arxiv_id_norm and ...` est falsy → guard de dédup skippé → doublons silencieux chaque semaine.

**Fix requis avant tout autre développement :**

```python
# Clé canonique unifiée
def canonical_paper_id(arxiv_id: str, title: str) -> str:
    if arxiv_id:
        return f"arxiv:{normalize_arxiv_id(arxiv_id)}"
    return f"s2:{hashlib.md5(title.lower().strip().encode()).hexdigest()[:16]}"

# seen-arxiv-ids.txt → seen-paper-ids.txt
# Guard: if canonical_id in seen_ids → skip (couvre les 2 types)
```

**Pas de changement au scoring, au format de sortie, ni aux domaines.**

---

### 3.2 paper_synthesizer.py — Track A (Migration Gemini → Claude Haiku)

#### Entrées
- `_inbox/raw/papers/{domain}/*.md` (abstract + metadata, jamais full-text)
- Frontmatter attendu : `arxiv_id` ou `paper_id` canonique, `title`, `abstract`, `domain`, `tier`

#### Modèle et API
- **Modèle :** `claude-haiku-4-5` via Anthropic Batch API (50% discount)
- **Prompt caching :** `cache_control: {"type": "ephemeral"}` sur le bloc `system` (identique pour les 45 papers → ~44 cache hits/semaine)
- **Polling :** 60s interval, timeout 2h
- **Sur timeout :** écrire `batch_job_id` + timestamp dans `_logs/synthesizer-last-run.json`. Récupérable pendant 29 jours.

#### Contrat de prompt (System)

```
Tu es un synthétiseur de connaissances pour un vault Obsidian personnel en français.

RÈGLES ABSOLUES :
1. DÉRIVER LE CLAIM, NE PAS TRADUIRE. Reformule en partant du sens, pas du texte.
2. MITOSE COGNITIVE : Identifie d'abord tous les concepts distincts (liste numérotée).
   Produis ensuite UN fichier par concept. Jamais de note agrégée.
3. TITRE DÉCLARATIF : Chaque titre est une affirmation testable en français.
   Exemples corrects : "Le prefetching DNS réduit la latence perçue de 15-40%"
   Exemples incorrects : "À propos du prefetching DNS", "DNS Prefetching Notes"
4. JAMAIS plus de 5 mots consécutifs copiés de la source.
5. TIER ASSIGNMENT (S/A/B/C) :
   - S : insight fondamental, applicable immédiatement, change une pratique
   - A : insight solide, applicable avec effort, enrichit une pratique
   - B : contexte utile, une ligne dans le digest suffit
   - C/D : bruit — ignorer

[cache_control: ephemeral appliqué à ce bloc]
```

#### Format de sortie (JSON par paper)

```json
{
  "paper_id": "arxiv:2401.12345",
  "concepts": [
    {
      "tier": "S",
      "title": "Le titre déclaratif en français",
      "body": "Corps de la note en français (reformulé, pas traduit)",
      "type": "concept|discovery|anti-bug|pattern|decision",
      "source_chain": ["origin: https://arxiv.org/abs/2401.12345", "via: abstract"],
      "cross_ref_candidates": ["<!-- candidate: concept connexe -->"]
    }
  ],
  "digest_line": "Une ligne Tier B si applicable (null sinon)"
}
```

#### Fichiers de sortie

| Tier | Destination | Nom |
|------|-------------|-----|
| S / A | `_inbox/raw/concepts/A-{paper_id}.md` | 1 fichier/concept |
| B | `universal/research/` via `_inbox/raw/` | ligne dans `digest-{domain}-W{N}.md` |
| C / D | Ignoré | — |

**Idempotence :** si `A-{paper_id}-{n}.md` existe → skip ce concept. Jamais d'écrasement.

> **Note multi-concepts :** Un paper avec N concepts Tier S/A produit N fichiers distincts.  
> Naming : `A-{paper_id_sanitized}-1.md`, `A-{paper_id_sanitized}-2.md`, etc.  
> Le concept index (1, 2…) correspond à l'ordre de la liste numérotée produite par le prompt Mitose.

#### Fallback Track A

```json
// _logs/synthesizer-last-run.json sur timeout
{
  "status": "timeout",
  "batch_job_id": "batch_01...",
  "submitted_at": "2026-04-13T18:05:00Z",
  "recoverable_until": "2026-05-12T18:05:00Z",
  "papers_submitted": 45,
  "papers_completed": 0
}
```

---

### 3.3 nightly-agent.sh — Guard de Concurrence (BS-2)

**Problème identifié :** Aucun guard → deux instances concurrentes possibles si un run dépasse 24h.

**Fix requis en tête du script :**

```bash
# Concurrency guard — doit être la première ligne utile du script
LOCKFILE="$VAULT/_logs/nightly.lock"
exec 200>"$LOCKFILE"
flock -n 200 || { echo "[$(date)] Nightly already running, skipping." >> "$VAULT/_logs/nightly-agent.log"; exit 0; }
trap "flock -u 200; rm -f $LOCKFILE" EXIT
```

---

### 3.4 Track B — NotebookLM MCP

#### Prérequis de sécurité (non-négociables)

| Exigence | Détail |
|----------|--------|
| **Compte Google dédié** | Créer un compte Google réservé à l'automation. Jamais le compte personnel. |
| **MCP forké et pinné** | Forker `m4yk3ldev/notebooklm-mcp`. Pinner le commit SHA exact dans `package.json`. Auditer avant chaque mise à jour. |
| **Chrome profile isolé** | `--user-data-dir=/Users/djemildavid/.nlm-automation-chrome` — aucun autre site connecté dans ce profil |
| **auth.json permissions** | `chmod 600 ~/.notebooklm-mcp/auth.json` après chaque auth setup |
| **Abstract only** | Jamais de full-text. Uniquement abstract + titre + DOI + arxiv_id. |

#### Opérations Track B (dans l'ordre)

```
1. Lire _meta/nlm-notebooks.json (source counts par domaine + notebook IDs)
2. Pour chaque domaine avec de nouveaux papers :
   a. Si source_count >= 45 → rotation (voir §3.4.1)
   b. add_source_text : abstract + titre + paper_id (pas de full-text)
   c. Mettre à jour nlm-notebooks.json (source_count++)
3. generate_summary_report : cross-domain insights (1 par domaine)
4. Pour chaque concept Tier S dans Track A output :
   notebook_query → grounding verdict (voir §3.4.2)
5. Écrire B-{paper_id}-grounded.md pour chaque Tier S avec verdict
6. Écrire nlm-status.json : complete: true, timestamp, stats
```

**Wrap :** `caffeinate -i <script Track B>` — empêche le sleep macOS.  
**Sur ConnectionReset / timeout :** écrire `complete: false` dans `nlm-status.json`, exit propre.

#### 3.4.1 Rotation des Notebooks (fix BS-6)

**Stratégie :** sliding window 2 notebooks par domaine.

```json
// _meta/nlm-notebooks.json
{
  "schema_version": 1,
  "domains": {
    "ai": {
      "current": { "id": "nb_abc123", "source_count": 38, "created": "2026-04-06" },
      "previous": { "id": "nb_xyz789", "source_count": 45, "created": "2026-03-02" }
    },
    "iot": { "current": {...}, "previous": {...} },
    "cloud": { "current": {...}, "previous": {...} },
    "ecommerce": { "current": {...}, "previous": {...} }
  }
}
```

- À 45 sources : `current` → `previous`, créer nouveau `current`  
- `notebook_query` interroge **current + previous** (sliding window) → le contexte accumulé n'est jamais perdu au moment de la rotation  
- Écriture **atomique** : `write to nlm-notebooks.json.tmp` → `rename to nlm-notebooks.json`  
- Alert dans `last-nightly.json` : `notebook_rotations: [{domain, date}]`

#### 3.4.2 Grounding Verdict — Enum et Sémantique (fix BS-3)

**Enum défini :**

| Verdict | Signification | Traitement vault |
|---------|---------------|------------------|
| `supported` | NLM confirme le claim sur 2+ sources | Note éligible à promotion standard |
| `partially_supported` | NLM confirme partiellement | Note éligible, sans accélération |
| `disputed` | NLM cite des sources contradictoires | `maturity: fleeting` forcé + `<!-- review-flag: nlm-disputed -->` |
| `insufficient_evidence` | Trop peu de sources pour trancher | Note traitée comme si pas de grounding |

**Frontmatter Track B :**

```yaml
---
type: concept
maturity: fleeting
tier: S
created: 2026-04-13
source_chain:
  - "origin: https://arxiv.org/abs/2401.12345"
  - "via: abstract"
arxiv_id: "2401.12345"
nlm_grounding:
  verdict: supported
  confidence: 0.87
  notebook_ids: ["nb_abc123", "nb_xyz789"]
---
```

---

### 3.5 Nightly Agent — Étapes Modifiées

#### Étape 0 — Guard (étendu)

```
Vérifications dans l'ordre (tout fail → abort + log) :
1. flock acquis (voir §3.3)
2. note_count < 285 → si ≥285 : HARD GATE, émettre review-required.md
3. fleeting_count : si ≥15 → PAUSE synthèse, émettre vault-health-alert.md, continuer pour lint uniquement
4. nlm-status.json → si complete: true : activer B-track intake
5. batch_job_id sans draft files correspondants → alert dans last-nightly.json
6. overflow_count → si >0 : traiter min(overflow_count, 5) en FIFO avant inbox normal
```

#### Étape 2 — Intake unifié A+B (étendu)

```
1. Schéma frontmatter requis (les 2 tracks) :
   type, maturity, tier, created, source_chain, paper_id
   → fichier rejeté vers _inbox/quarantine/ si champ manquant

2. Déduplication :
   - Clé = paper_id (arxiv:{id} ou s2:{hash})
   - Sur collision A+B : A-track gagne, B-track fournit nlm_grounding
   - Merge : note A enrichie avec le champ nlm_grounding de B

3. Atomisation B-track (Claude, même session) :
   Prompt : "Dériver le claim de cette prose NLM en une note vault française.
   Ne pas traduire. Titre déclaratif obligatoire.
   Si nlm_grounding.verdict = 'disputed' : ajouter <!-- review-flag: nlm-disputed -->
   Liens non résolus → <!-- candidate: X --> jamais de wikilinks directs."

4. Mitose post-atomisation : si le résultat contient >1 concept → splitter

5. Cap : 15 fichiers/run (overflow → _inbox/overflow/ FIFO)
   Ordre de priorité : overflow d'abord, inbox ensuite
   Les fichiers overflow comptent dans le cap de 15 (pas en supplément).
   Ex. : 5 overflow + 10 inbox = 15 total. Jamais plus de 15/run.

6. Bootstrap mode (fix BS-5) : si vault_notes < 50 → désactiver recency window cross-refs
```

#### Étape 3 — Cross-refs (pré-filtre)

```
1. Avant l'agent : script produit _inbox/cross-ref-candidates.json
   Filtre : tag-intersection + recency (dernières 8 semaines)
   Résultat : 20-30 notes maximum
   Bootstrap : si vault < 50 notes → toutes les notes sans filtre

2. Agent lit uniquement cross-ref-candidates.json (pas le vault complet)
   → max 10 cross-refs annotées par run
   → max 1 bridge note → _inbox/review/

3. Format obligatoire : [[note]] — raison en 1 phrase (jamais de wikilink nu)
```

#### Étape 5 — INDEX incrémental

```
1. Lire last-nightly.json → liste des notes touchées depuis dernier run
2. INDEX diff : mettre à jour uniquement ces notes (pas de rebuild complet)
3. MOC : régénérer uniquement les MOC dont un tag a changé de count
4. enrichment_status dans last-nightly.json :
   {track_b_active, last_nlm_success, consecutive_failures, notebook_rotations}
5. Si consecutive_failures >= 2 : écrire _inbox/ALERT-nlm-degraded.md
```

#### Étape 6 — Health metrics

```json
// last-nightly.json v6 schema
{
  "status": "success|partial|failed",
  "last_run": "ISO8601",
  "notes_added": 0,
  "tokens_used": 0,
  "tier_distribution": {"S": 0, "A": 0, "B": 0},
  "errors": [],
  "enrichment_status": {
    "track_b_active": true,
    "last_nlm_success": "ISO8601",
    "consecutive_failures": 0,
    "notebook_rotations": []
  },
  "health": {
    "backlog_inbox": 0,
    "overflow_count": 0,
    "fleeting_count": 0,
    "orphan_count": 0,
    "oldest_unreviewed_days": 0,
    "note_count": 0,
    "ceiling_pct": 0.0
  }
}
```

---

## 4. Contrats de Données

### 4.1 Frontmatter Schema Commun (les 2 tracks)

```yaml
---
type: concept|decision|pattern|discovery|anti-bug|bridge|literature  # REQUIRED
maturity: fleeting                                                      # REQUIRED, always fleeting
tier: S|A|B                                                            # REQUIRED
created: YYYY-MM-DD                                                     # REQUIRED
paper_id: "arxiv:2401.12345" | "s2:abc1234567890abc"                  # REQUIRED (canonical key)
source_chain:                                                           # REQUIRED (≥1 entrée)
  - "origin: URL ou chemin"
  - "via: abstract|full-text|notebooklm"
nlm_grounding:                                                          # OPTIONAL (Track B seulement)
  verdict: supported|partially_supported|disputed|insufficient_evidence
  confidence: 0.0–1.0
  notebook_ids: ["nb_xxx"]
---
```

Tout fichier manquant un champ `REQUIRED` est rejeté vers `_inbox/quarantine/` avec un message d'erreur lisible.

### 4.2 Fichiers Sentinelles

| Fichier | Producteur | Consommateur | Signification |
|---------|-----------|-------------|---------------|
| `_logs/nlm-status.json` | Track B | Étape 0 | `complete: true` = Track B prêt |
| `_logs/synthesizer-last-run.json` | Track A | Étape 0, integrity-check | `batch_job_id` pour recovery |
| `_meta/nlm-notebooks.json` | Track B | Track B | IDs + source counts, atomic write |
| `_inbox/ALERT-nlm-degraded.md` | Étape 5 | Djemil (review) | NLM down ≥2 semaines |
| `_inbox/overflow/` | Étape 2 | Étape 0 (FIFO) | Surplus cap-15 |
| `_inbox/quarantine/` | Étape 2 | Djemil (review) | Fichiers schema invalide |
| `_logs/nightly.lock` | nightly-agent.sh | nightly-agent.sh | Guard concurrence flock |

### 4.3 Naming Convention Fichiers

```
Track A : A-{paper_id_sanitized}.md
           ex: A-arxiv-2401.12345.md
               A-s2-abc1234567890abc.md

Track B : B-{paper_id_sanitized}-grounded.md
           ex: B-arxiv-2401.12345-grounded.md

Digest  : digest-{domain}-W{YYYY-WN}.md
           ex: digest-ai-W2026-16.md
```

`paper_id_sanitized` = remplacer `:` et `.` par `-`.

---

## 5. Modèle de Sécurité

| Risque | Mitigation |
|--------|-----------|
| ToS Google (CDP automation) | Compte Google dédié automation, isolé du compte personnel |
| auth.json = session Google en clair | `chmod 600`, Chrome profile isolé, rotation périodique |
| Supply chain (package 7 étoiles) | Fork + audit du code source + pin hash commit exact |
| CDP scope = tout le navigateur | Chrome profile `--user-data-dir` dédié, aucun autre site connecté |
| Papers pré-publication vers Google | Abstract uniquement (jamais full-text), vérifier licence avant ajout |

**Compte dédié :** L'email du compte automation NE DOIT PAS apparaître dans `notebooklm-context-global.md` ni dans aucune note vault. Isolation complète.

---

## 6. Modèle de Fiabilité

### Circuit Breaker Track B

```
État CLOSED (normal) :
  Track B s'exécute, écrit nlm-status.json complete:true

État OPEN (auth failure | crash | timeout) :
  → nlm-status.json : complete: false, reason: "auth|crash|timeout"
  → Nightly agent : Étape 0 détecte → skip B-track intake
  → Track A output seul → pipeline complet, qualité réduite mais fonctionnel
  → consecutive_failures++ dans last-nightly.json

État ALERT (consecutive_failures >= 2) :
  → _inbox/ALERT-nlm-degraded.md créé
  → enrichment_status visible dans last-nightly.json
  → Re-auth manuelle requise (ouvrir Chrome, relancer setup_auth)
```

### Idempotence

| Composant | Mécanisme |
|----------|-----------|
| Track A | Filename = paper_id → skip si fichier existe |
| Track B | `add_source_text` : paper_id comme source ID, NLM déduplique |
| Nightly agent | Étape 0 guard date + flock concurrence |
| INDEX | Diff incrémental (seulement notes touchées) |

### Timing Sunday Pipeline

```
Deadline : 23h30 pour que nlm-status.json soit complete:true
Budget indicatif :
  Track A : 20-40 min (Batch API async)
  Track B : 15-35 min (add_source × 45 + research)
  Total estimé : 35-75 min
  Marge : ~4-5h avant nightly 2h17

Si Track B dépasse 23h30 : écrire complete: false + exit propre
  → Nightly agent 2h17 traite Track A seul
```

---

## 7. Invariants PKM — Enforcement par Design

Tous les invariants s'appliquent aux deux tracks. Le prompt nightly pour l'atomisation B-track inclut les mêmes contraintes que paper_synthesizer.

| Invariant | Enforcement |
|-----------|-------------|
| Titre déclaratif | Prompt : "affirmation testable en français" + exemples positifs/négatifs |
| Anti-Collector's Fallacy | Prompt : "Dériver le claim, ne pas traduire. Maximum 5 mots consécutifs de la source." |
| Mitose Cognitive | Prompt : étape 1 = liste numérotée des concepts, étape 2 = 1 fichier/concept. Assert : si input >1 concept et output = 1 fichier → flag |
| maturity: fleeting | Hardcodé dans le générateur. Jamais configurable par prompt. |
| Liens annotés | Prompt + post-processing : wikilinks nus → reject. Format : `[[note]] — raison` |
| Liens non-résolus | → `<!-- candidate: X -->` HTML comments. Jamais de wikilinks vers des notes inexistantes |
| 300-note ceiling | Étape 0 guard hard gate à 285 |

---

## 8. Patterns d'Hybridation Livrés

| Pattern | Description | Statut |
|---------|-------------|--------|
| **P1 — Replace** | Claude Haiku remplace Gemini, EU-safe | Livré par Track A |
| **P2 — Ground** | NLM vérifie les claims Tier S contre les sources | Livré par Track B (nlm_grounding verdict) |
| **P3 — Discover** | NLM génère des insights cross-domaines → Claude atomise | Livré par `generate_summary_report` → Étape 2 |
| **P4 — Accumulate** | Notebooks croissent semaine après semaine, sliding window 2 notebooks | Livré par rotation + query current+previous |

---

## 9. Dette Technique Documentée

### Medium (prochaine itération)

| ID | Description | Impact si non résolu |
|----|-------------|---------------------|
| DT-M1 | `integrity-check.sh` n'enforce pas le ceiling automatiquement | Manuel seulement jusqu'à 285 notes |
| DT-M2 | Pattern Accumulate sans décroissance temporelle | Papers >24 mois peuvent remonter comme "nouveaux insights" |
| DT-M3 | `notebooklm-context-global.md` contient un profil personnel — devrait être anonymisé avant push NLM | Exposition minimale mais réelle |
| DT-M4 | Assertion `batch_job_id` sans draft files manquante dans `integrity-check.sh` | Silencieux seulement — alerté dans last-nightly.json |
| DT-M5 | Cross-ref cold-start: recency window trop restrictif avant 50 notes | Fix bootstrap mode décrit mais non implémenté |

### Low (backlog)

| ID | Description |
|----|-------------|
| DT-L1 | `add_source_text` : 45 appels séquentiels (~3 min) — acceptable |
| DT-L2 | launchd sans retry policy sur outage API — nightly-skipped.flag recommandé |
| DT-L3 | Coût nightly agent (~$115/an) — instrumenter token split réel avant d'optimiser |

---

## 10. Prérequis de Déploiement

Avant d'écrire la moindre ligne de code :

- [ ] Créer un compte Google dédié automation (email distinct du compte personnel)
- [ ] Forker `m4yk3ldev/notebooklm-mcp` → auditer le source → pinner le hash commit dans package.json
- [ ] Créer `_meta/nlm-notebooks.json` avec le schéma vide (4 domaines, current + previous null)
- [ ] Créer `_logs/nlm-status.json` initial : `{"status": "not_initialized"}`
- [ ] Tester `caffeinate -i` wrapping sur une opération longue pour confirmer le comportement sleep
- [ ] Confirmer que `ANTHROPIC_API_KEY` est dans `~/.zshenv` (permanent, pas seulement `~/.zshrc`)

---

## 11. Ordre d'Implémentation Recommandé

```
Sprint 1 — Débloquer immédiatement (sans NLM)
  1. Fix corpus_collector.py : canonical paper_id (BS-1)
  2. Migrer paper_synthesizer.py : Gemini → Claude Haiku Batch + cache_control
  3. Fix nightly-agent.sh : flock concurrency guard (BS-2)
  4. Fix nightly prompt : Étape 0 overflow drain + bootstrap cross-refs
  Résultat : 51 papers traités, pipeline quotidien fiable

Sprint 2 — Intégrer Track B
  5. Créer nlm-notebooks.json + compte Google dédié
  6. Implémenter Track B script (caffeinate, rotation, sentinel)
  7. Étendre Étape 2 : merge A+B, dedup paper_id, grounding verdict routing
  8. Étendre Étape 5 : enrichment_status + ALERT
  Résultat : 4 patterns d'hybridation actifs

Sprint 3 (dette technique)
  9. integrity-check.sh : ceiling assertion + batch_job_id check
  10. Bootstrap cross-refs mode
  11. Recency decay pour Pattern 4
```

---

## Annexe A — Mapping Failles → Fixes

| Faille | Sévérité | Fix intégré dans |
|--------|----------|-----------------|
| F1 ToS Google | Critical | §5 Sécurité — compte dédié |
| F2 auth.json clair | Critical | §5 chmod 600 + Chrome isolé |
| F3 Supply chain | Critical | §3.4 Fork + pin hash |
| F4 Pas de contrat données | Critical | §4 Contrats de données |
| F5 Déduplication absente | Critical | §3.5 Étape 2, paper_id key |
| F6 Anti-Collector's Fallacy | Critical | §7 Invariants PKM |
| F7 Mitose non enforcée | Critical | §7 Invariants PKM |
| F8 Wikilinks fantômes | Critical | §3.5 Étape 2, HTML comments |
| F9 Budget INDEX | Critical | §3.5 Étape 5, INDEX diff |
| F10 Cross-refs sans filtre | Critical | §3.5 Étape 3, candidates.json |
| F11 macOS sleep | High | §3.4 caffeinate -i |
| F12 Race condition Track B | High | §3.4 Sentinel 23h30 |
| F13 Batch timeout sans output | High | §3.2 batch_job_id recovery |
| F14 Re-run non idempotent | High | §3.2 filename = paper_id |
| F15 File-count guard absent | High | §3.5 Étape 2 cap 15 |
| F16 CDP scope | High | §5 Chrome profile dédié |
| F17 Papers pré-pub | High | §3.4 Abstract only |
| F18 Queue review insoutenable | High | §3.5 cap 5/track + alerte 15 |
| F19 Tier asymétrique | High | §3.2/3.4 Tier rubric dans les 2 prompts |
| F20 NLM 50-source limit | High | §3.4.1 Rotation @45 |
| F21 Notebook ID sans owner | High | §3.4 nlm-notebooks.json atomic |
| F22 Prompt caching absent | High | §3.2 cache_control ephemeral |
| F23 Circuit breaker invisible | Medium | §6 enrichment_status + ALERT |
| F24 Digest bypass staging | Medium | §4.2 Tous les outputs via _inbox/ |
| F25 Accumulate sans décroissance | Medium | DT-M2 dette technique |
| F26 Batch results expiry | Medium | DT-M4 dette technique |
| BS-1 S2 dedup invisible | High | §3.1 canonical paper_id |
| BS-2 Concurrence nightly | High | §3.3 flock guard |
| BS-3 Grounding verdict undef | Medium | §3.4.2 enum + routing |
| BS-4 Overflow sans drain | Medium | §3.5 Étape 0 FIFO drain |
| BS-5 Cold-start cross-refs | Medium | §3.5 Étape 3 bootstrap mode |
| BS-6 Rotation détruit contexte | Medium | §3.4.1 Sliding window 2 notebooks |
