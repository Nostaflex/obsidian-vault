# Second Brain v5 — Architecture Spec
Date: 2026-04-12
Status: implemented (Sprint 1+2) / partial (Sprint 3+4)

---

## 1. Objectif

Transformer un flux de papers scientifiques bruts en notes atomiques pertinentes, structurées, grounded dans les sources, avec zéro Collector's Fallacy.

Contrainte principale : pipeline 100% automatisé sur coûts prévisibles (subscription Claude Code + APIs gratuites uniquement).

---

## 2. Pipeline global

Quatre composants s'enchaînent selon un pattern "write-to-folder" découplé :

```
arXiv / Semantic Scholar
        │
        ▼
corpus_collector.py ──────► _inbox/raw/papers/
                                    │
                             (Option A)│(Option B)
                                    │        │
                            NotebookLM    paper_synthesizer.py
                         (session hebdo)  (fallback automatisé)
                                    │        │
                                    ▼        ▼
                        _inbox/raw/digests/  _inbox/raw/concepts/
                                         │
                                         ▼
                                  Nightly Agent (2h17)
                                         │
                                         ▼
                            universal/ | projects/ (notes atomiques)
```

### 2.1 Rythme d'orchestration

| Composant | Déclencheur | Rythme |
|-----------|-------------|--------|
| corpus_collector.py | launchd | Samedi 10h |
| NotebookLM synthesis (primary) | Manuel / session interactive | Samedi/dimanche |
| paper_synthesizer.py (fallback) | launchd | Dimanche 10h |
| Nightly agent | launchd | 2h17 quotidien |

### 2.2 Pattern "write-to-folder"

Tous les composants écrivent dans `_inbox/` et le nightly agent consomme indépendamment. Ce découplage garantit :
- Pas de dépendance temporelle entre les étapes (chaque composant peut échouer sans bloquer les autres)
- Idempotence : le nightly agent vérifie `_meta/LOG.md` avant de traiter un fichier (anti re-ingestion)
- Observabilité : l'état de `_inbox/` reflète à tout moment le backlog non traité

---

## 3. Composants

### 3.1 corpus_collector.py

Collecte et filtre des papers depuis arXiv et Semantic Scholar. Point d'entrée du pipeline.

**Sources :**
- arXiv API (gratuit, sans clé) — par catégorie, fenêtre configurable
- Semantic Scholar API (gratuit, sans clé) — enrichissement citation_count

**Scoring composite (0.0–1.0) :**

| Composante | Poids | Détail |
|------------|-------|--------|
| vault_relevance | 0.4 | Tags actifs du vault présents dans titre+abstract |
| citation_velocity | 0.3 | citationCount normalisé (log scale, max 1000) |
| recency | 0.3 | 1.0 si <7j / 0.7 si <30j / 0.4 si <90j / 0.1 sinon |

**Tiers :**

| Tier | Seuil | Traitement downstream |
|------|-------|----------------------|
| S | score > 0.8 | Note complète par synthesizer |
| A | score > 0.5 | Note complète par synthesizer |
| B | score > 0.3 | 1-liner dans digest |
| C | score ≤ 0.3 | Ignoré |

**Règles :**
- Max 5 papers retenus par domaine par run
- Déduplication sur `arxiv_id` normalisé (registre dans `_logs/seen-arxiv-ids.txt`)
- Output : `_inbox/raw/papers/{domain}-{YYYY-MM-DD}.md`

### 3.2 NotebookLM (chemin principal)

Rôle : couche de distillation grounded — RAG fermé sur les papers, zéro hallucination par construction.

**Mode d'utilisation : session interactive hebdomadaire**
- Déclencheur : session Claude Code interactive (pas `--print`)
- Via notebooklm-mcp (PleasePrompto) ou export manuel depuis l'UI Google
- Output : markdown dans `_inbox/raw/digests/digest-{domain}-W{N}.md`
- Format attendu : Study Guide OU Briefing Doc exporté depuis NotebookLM

**Pourquoi pas en automatique :**
- `claude --print` n'initialise pas les connexions MCP
- Pas d'API NotebookLM officielle publique (Enterprise alpha uniquement)
- `notebooklm-py` (unofficial) est fragile — peut casser à chaque update Google

**Fallback automatique :** si aucun digest dans `_inbox/raw/digests/` → paper_synthesizer.py prend le relais sur les raw papers.

### 3.3 paper_synthesizer.py (fallback automatisé)

Rôle : synthèse automatique des papers quand NotebookLM n'est pas disponible ou n'a pas tourné.

**Paramètres techniques :**
- API : Gemini 2.0 Flash (Google, gratuit — 1M tokens/jour, 15 RPM free tier)
- Coût : $0
- Rate limiting : 4s entre appels (respecte 15 RPM)

**Outputs :**
- Output 1 : pre-notes atomiques dans `_inbox/raw/concepts/draft-{concept}.md` (1 fichier par concept, tiers S/A)
- Output 2 : digest littérature dans `universal/research/digest-{domain}-W{N}.md` (tiers B en 1-liner)

**Règle de filtrage :**
- Tier S/A → note complète (concept extraction atomique)
- Tier B → 1-liner dans digest
- Tier C → ignoré

**Point critique :** paper_synthesizer produit des concept extractions atomiques, pas des digests blob. Chaque fichier `draft-*.md` = 1 concept = 1 futur note. Évite la double passe de synthèse par le nightly agent.

### 3.4 Nightly agent (Light Mode v5)

Rôle : intégration des drafts inbox en notes finales, maintenance du vault, lint, rebuild INDEX.

**Mode :** Light — enrichissement depuis `_inbox/session/` et `_inbox/raw/` uniquement. Pas de WebSearch.

**Budget tokens v5 :**

| Phase | Budget | Action si dépassé |
|-------|--------|-------------------|
| Steps 1-3 (ingest + cross-refs) | 20 000 tokens | Terminer note en cours, passer Step 4 |
| Step 4 (lint) | 5 000 tokens | Arrêt propre, noter dans maintenance-report.md |
| Steps 5-6 (rebuild + finalize) | 5 000 tokens | Toujours exécuté même si budget dépassé avant |
| Hard stop total | 35 000 tokens | status=partial dans last-nightly.json |

Note : budget Steps 1-3 réduit de 40k (v4) à 20k (v5) car paper_synthesizer.py pré-synthétise les concepts avant ingest.

**Pipeline (ordre strict) :**

**Étape 0 — Guard pre-run (0 token)**
- Exécuter `integrity-check.sh`
- Vérifier `_inbox/` et `_logs/last-nightly.json` → skip si inbox vide ET lint < 3 jours
- Écrire `_logs/last-nightly.json` status=in_progress

**Étape 1 — Traiter `_inbox/session/`**
- Anti re-ingestion : grep dans `_meta/LOG.md` avant traitement
- Mitose cognitive : si >2 concepts distincts → N notes séparées
- Appliquer template obligatoire, vérifier wikilinks contre `/tmp/INDEX_rebuilt.md`
- Déplacer vers `_inbox/session/_processed/` après traitement

**Étape 2 — Traiter `_inbox/raw/`**
- 2A — `_inbox/raw/concepts/` : fichiers pre-synthétisés par paper_synthesizer. NE PAS re-synthétiser. Valider frontmatter + titre, retirer préfixe `draft-`, déplacer vers destination finale.
- 2B — `_inbox/raw/articles/`, `_inbox/raw/docs/`, `_inbox/raw/repos/` : extraction complète depuis les sources brutes, mitose cognitive, règle anti Collector's Fallacy.

**Étape 3 — Cross-références**
- Pour chaque note créée : chercher notes partageant ≥1 tag commun dans INDEX
- Ajouter lien annoté dans `## Liens` des notes existantes (max 10 notes mises à jour par run)
- Bridge Notes (1 max/run) : si connexion cross-domaine forte → draft dans `_inbox/review/bridge-draft-{a}-{b}.md`, attend validation Djemil

**Étape 4 — Lint actif**
- 4a : auto-corrections silencieuses (liens cassés corrigibles, sections `## Liens` absentes)
- 4b : orphelines depuis >30j → tag `maturity: archive-candidate`
- 4c : wikilinks cassés non auto-corrigibles → signalement dans `maintenance-report.md`
- 4d : candidats archivage (0 hit depuis 90j) → signalement uniquement, pas d'archivage auto
- 4e : contradictions potentielles (même tag, affirmations opposées) → signalement
- 4f : review queue — 3 notes fleeting les plus anciennes dans `_inbox/review/weekly-review-W{N}.md`

**Étape 5 — Régénérer INDEX.md + context-cards + MOC**
- INDEX.md structuré (par projet + par type), résumé 10 mots par note depuis `## Essentiel`
- Context-cards : régénérés (max 200 tokens, 3 sections, 5 liens/section)
- MOC auto : pour chaque tag ≥5 notes → `_meta/moc/moc-{tag}.md`

**Étape 6 — Finaliser**
- Agréger `_meta/signals.md` si >100 lignes
- Écrire `_logs/last-nightly.json` (status, métriques, health)

---

## 4. Lifecycle des notes

```
[Source externe]
     │
     ▼
fleeting (créée par agent)
     │
     │  Djemil lit, enrichit, valide
     ▼
literature (note de lecture structurée)
     │
     │  Djemil relie, synthétise, exprime
     ▼
evergreen (principe durable, tenu à jour)
```

Règle fondamentale : seul Djemil peut promouvoir. L'agent crée uniquement en `maturity: fleeting`. Les notes non lues restent identifiées comme telles — le statut fleeting est un signal d'arriéré, pas une étape automatique.

Cas spécial — Bridge Notes : créées par l'agent dans `_inbox/review/` avec `type: bridge`, attendent validation avant d'être déplacées vers `universal/` ou `projects/`.

---

## 5. Template de note

```yaml
---
type: concept | decision | pattern | discovery | anti-bug | bridge | literature
maturity: fleeting
tier: S | A | B
created: YYYY-MM-DD
source_chain:
  - "origin: URL ou chemin source primaire"
  - "via: chemin intermédiaire si applicable"
---
```

```markdown
# [Titre déclaratif — phrase affirmative testable]

Tags: #tag1 #tag2

## Essentiel
[Compression 2 étapes : (1) identifier l'essence, (2) reformuler dans ses propres mots.
JAMAIS plus de 5 mots consécutifs copiés de la source. Max 3 lignes.]

## Détail
[Contenu complet reformulé]

## Liens
- [[note-existante]] — raison du lien en 1 phrase

<!-- generated: YYYY-MM-DD -->
```

---

## 6. Règles qualité

### 6.1 Titres déclaratifs

Le titre DOIT être une phrase affirmative testable (peut être vraie ou fausse).

- BON : "Le cache fetch de Next.js 15 utilise no-store par défaut"
- MAUVAIS : "Notes sur le cache Next.js 15"
- BON : "L'atomicité des notes facilite la recombinaison cross-domaine"
- MAUVAIS : "Atomicité des notes"

Si aucun titre déclaratif clair n'est possible → le concept est mal scopé. Diviser en plusieurs notes ou approfondir.

### 6.2 Anti Collector's Fallacy

L'agent ne copie jamais. Il reformule toujours.

Test : si `## Essentiel` contient >5 mots consécutifs copiés de la source → recommencer la section. La reformulation dans ses propres mots est le signal minimal qu'une idée a été assimilée.

### 6.3 Mitose cognitive

Si une source contient plus de 2 concepts distincts → créer N notes séparées, pas 1 note fourre-tout.

Test "fonction pure" pour chaque note créée : est-elle compréhensible sans les autres notes de la même source ? Si non → trop couplée, reformuler.

### 6.4 Bridge Notes

Une Bridge Note capture pourquoi deux concepts de domaines différents s'éclairent mutuellement. Elle est créée quand l'agent détecte une connexion cross-domaine forte (ex : concept AI applicable à un problème IoT ou ecommerce).

Cycle de vie : créée dans `_inbox/review/bridge-draft-{a}-{b}.md` avec `type: bridge` → validation Djemil → déplacée vers `universal/` ou `projects/`. Maximum 1 bridge note créée par run pour rester sous budget.

### 6.5 Liens annotés

Format obligatoire dans `## Liens` :
```
- [[slug-note]] — raison du lien en 1 phrase
```

Jamais de lien nu (`[[note]]` sans annotation). Tout lien doit justifier sa présence. Un lien n'est écrit que si la cible est confirmée dans `/tmp/INDEX_rebuilt.md` au moment de l'écriture (anti-hallucination).

---

## 7. Fichiers clés

| Fichier | Rôle |
|---------|------|
| `.nightly-prompt.md` | Prompt du nightly agent (v5) |
| `VAULT.md` | Conventions du vault (filing rules, wikilink discipline) |
| `corpus_collector.py` | Collecte papers arXiv/Semantic Scholar, scoring, tier filter |
| `paper_synthesizer.py` | Synthèse Gemini 2.0 Flash (fallback automatisé) |
| `nightly-agent.sh` | Wrapper shell pour lancement launchd du nightly agent |
| `integrity-check.sh` | Pre-run guard : vérifie l'intégrité structurelle du vault |
| `_meta/INDEX.md` | Index structuré des notes (par projet + par type) |
| `_meta/LOG.md` | Journal append-only anti re-ingestion |
| `_meta/signals.md` | Fenêtre active des notes consultées |
| `_meta/lint-ignore.txt` | Patterns ignorés par le lint |
| `_meta/moc/moc-{tag}.md` | Maps of Content auto-générées (≥5 notes par tag) |
| `_logs/last-nightly.json` | Métriques dernière exécution nightly |
| `_logs/synthesizer-last-run.json` | Métriques dernière synthèse papers |
| `_logs/seen-arxiv-ids.txt` | Registre de déduplication des papers collectés |
| `_logs/broken-links.txt` | Wikilinks cassés détectés par integrity-check.sh |
| `_logs/maintenance-report.md` | Rapport lint actif (append) |
| `_inbox/review/` | Bridge drafts + weekly review queue, attendent validation Djemil |

---

## 8. Modèle de coûts

| Composant | Coût |
|-----------|------|
| Nightly agent (`claude --print`) | Inclus subscription Claude Code |
| corpus_collector.py | Gratuit (arXiv + Semantic Scholar, sans clé API) |
| paper_synthesizer.py | Gratuit (Gemini 2.0 Flash free tier — 1M tokens/jour) |
| NotebookLM (session interactive) | Gratuit (compte Google) |
| **Total variable** | **$0** |

---

## 9. Sprints

### Sprint 1 ✅ (2026-04-12)
- VAULT.md documenté (filing rules, wikilink discipline, zones d'accès)
- decisions/ aplati → wikilinks réparés
- integrity-check.sh corrigé (basename resolution pour les 4 faux positifs structurels)
- .nightly-prompt.md → v5 : frontmatter YAML complet, titres déclaratifs obligatoires, mitose cognitive, bridge notes, lint actif 6 étapes, budget tokens réduit à 35k total

### Sprint 2 ✅ (2026-04-12)
- corpus_collector.py : scoring composite (vault_relevance 0.4 / citation_velocity 0.3 / recency 0.3), tier filter S/A/B/C, déduplication arxiv_id, max 5/domaine
- paper_synthesizer.py : Gemini 2.0 Flash, concept extractions atomiques (draft-{concept}.md), digest tiers B, rate limiting 4s

### Sprint 3 ⬜
- Cross-refs embedding-based (claude-mem corpus) — dépasse le tag-matching tautologique actuel
- Weekly review generator automatisé
- Skill NotebookLM hebdomadaire (session interactive guidée)

### Sprint 4 ⬜
- Archive policy (_archive/ + règles de rétention)
- Index structuré Dataview-compatible (pour requêtes Obsidian)
- Prompt versioning (historique des changements de .nightly-prompt.md)

---

## 10. Décisions architecturales clés

### DA-1 : NotebookLM comme couche primaire, pas automatique
**Décision :** NotebookLM utilisé en session interactive hebdomadaire, pas intégré dans le pipeline automatisé launchd.
**Raison :** Pas d'API officielle stable (Enterprise alpha uniquement). La qualité supérieure (RAG fermé = zéro hallucination) justifie 5 minutes manuelles par semaine.
**Alternative rejetée :** `notebooklm-py` (librairie non officielle, fragile, peut casser à chaque update Google).

### DA-2 : paper_synthesizer produit des concept extractions, pas des digests blob
**Décision :** N fichiers `draft-{concept}.md` par domaine, pas 1 digest monolithique par run.
**Raison :** Évite la double passe de synthèse par le nightly agent (anti-pattern coûteux). Chaque draft = 1 concept déjà scopé = l'agent valide et déplace, pas synthétise à nouveau.

### DA-3 : Maturity fleeting par défaut — promotion humaine uniquement
**Décision :** Toute note créée automatiquement démarre à `maturity: fleeting`. Seul Djemil promeut à `literature` ou `evergreen`.
**Raison :** Évite le Collector's Fallacy numérique. Les notes non lues restent identifiables comme telles. Le statut fleeting = signal d'arriéré à traiter, pas étape franchie automatiquement.

### DA-4 : Gemini 2.0 Flash pour paper_synthesizer (pas Anthropic Batch API)
**Décision :** Gemini 2.0 Flash (free tier, 1M tokens/jour) pour la synthèse automatique des papers.
**Raison :** Coût $0 vs ~$0.01/semaine pour Anthropic Batch API. La qualité supérieure d'Anthropic n'est pas nécessaire pour ce cas d'usage (synthèse de papers → pre-notes, pas notes finales).

### DA-5 : Budget nightly agent réduit de 40k à 20k pour ingest (v4→v5)
**Décision :** Budget Steps 1-3 réduit de 40 000 à 20 000 tokens.
**Raison :** paper_synthesizer.py pré-synthétise les concepts avant ingest. L'agent n'a plus à synthétiser depuis les raw papers — il valide et déplace. Moins de travail cognitif = moins de tokens nécessaires.
