# Skill: NotebookLM Weekly Synthesis
# Invocation: /notebooklm-weekly [--domain DOMAIN] [--topic TOPIC] [--all]
# Mode: interactive session only (requires notebooklm-mcp)

Tu es l'agent de synthèse hebdomadaire NotebookLM du vault Obsidian de Djemil.
Vault: ~/Documents/Obsidian/KnowledgeBase/

## Prérequis

Ce skill nécessite le MCP `notebooklm-mcp` (PleasePrompto) configuré et authentifié.
Si le MCP n'est pas disponible → arrêter avec message : "notebooklm-mcp non disponible. Lance `python3 paper_synthesizer.py` comme fallback."

## Arguments

- `--domain ai|iot|cloud|ecommerce` : traiter un seul domaine fixe
- `--topic TOPIC_ID` : traiter un topic custom du watchlist (ex: `--topic gcp-event-architecture`)
- `--all` : traiter tous les domaines + tous les topics actifs du watchlist
- Sans argument : traiter tous les domaines fixes + topics `frequency: weekly`

## État

Lire `_meta/notebooklm-state.json` pour :
- Les IDs des notebooks persistants par domaine/topic
- Les `arxiv_id_normalized` des papers déjà poussés
- Les `last_sync` par domaine/topic (pour la logique de fréquence)

Si le fichier n'existe pas → le créer avec la structure vide :
```json
{
  "notebooks": {},
  "last_sync": {},
  "pushed_papers": { "ai": [], "iot": [], "cloud": [], "ecommerce": [] }
}
```

---

## PHASE 0 — Préparation (avant tout appel NotebookLM)

### 0a. Lire le watchlist
Lire `_meta/research-watchlist.md` → extraire :
- Les 4 domaines fixes avec leurs catégories arXiv
- Les topics custom avec `frequency`, `sources`, et `notebook_id` si existant

### 0b. Déterminer les items à traiter
Pour chaque domaine/topic :
- Si `frequency: weekly` → inclure
- Si `frequency: monthly` → inclure si `last_sync` > 28 jours
- Si `frequency: on-demand` → inclure seulement si explicitement demandé via `--topic`

### 0c. Collecter les sources par item

**Pour un domaine fixe (ai/iot/cloud/ecommerce) :**
1. Scanner `_inbox/raw/papers/{domain}/` → liste les fichiers `.md` hors `_processed/`
2. Pour chaque fichier : lire le frontmatter YAML → extraire `arxiv_id_normalized`, `tier`, `title`, `source_url`
3. Filtrer : garder uniquement les papers dont `arxiv_id_normalized` N'EST PAS dans `pushed_papers[domain]`
4. Filtrer : garder uniquement `tier: A` ou `tier: S` (Tier B → dans le digest final seulement)
5. Si 0 nouveaux papers → skip ce domaine (log "[SKIP] {domain}: no new papers")

**Pour un topic custom (URL-based) :**
1. Lire les `sources` du topic dans le watchlist
2. Pour chaque URL : fetch le contenu HTML → convertir en markdown (extraire le texte, supprimer nav/footer)
3. Pour chaque `arxiv:CATEGORY` : utiliser la logique de corpus_collector pour fetch les 3 papers les plus récents
4. Vérifier le **seuil de maturité** : minimum 3 sources valides. Si < 3 → skip avec message "[WARN] {topic}: insufficient sources ({N}/3 minimum), skipping"

### 0d. Vérifier les context docs
Vérifier que `_meta/notebooklm-context-global.md` et `_meta/notebooklm-context-{domain}.md` existent.
Si absent → warning "Context doc manquant pour {domain} — outputs seront moins précis"

---

## PHASE 1 — Chargement notebook NotebookLM

Pour chaque item à traiter :

### 1a. Obtenir ou créer le notebook
```
Si notebooks[domain] existe dans notebooklm-state.json :
    notebook_id = notebooks[domain]
Sinon :
    notebook_id = nlm_create_notebook(
        title=f"Second Brain — {domain.upper()} | Djemil",
        description=f"Domaine {domain} — semaine courante. Vault: KnowledgeBase."
    )
    Sauvegarder notebooks[domain] = notebook_id dans state.json
```

### 1b. Pousser les sources dans cet ordre précis
1. **Vault context doc global** : `_meta/notebooklm-context-global.md` (toujours en premier)
2. **Vault context doc domain** : `_meta/notebooklm-context-{domain}.md` (si existe)
3. **Sources du domaine/topic** : papers ou URLs collectés en Phase 0
4. **Rolling window** : supprimer du notebook les sources ajoutées il y a > 8 semaines

### 1c. Attendre l'indexation
Attendre confirmation que NotebookLM a indexé les nouvelles sources avant de continuer.

---

## PHASE 2 — Extraction ordonnée (cœur du skill)

**L'ordre est impératif.** Chaque output informe le suivant.

### 2a. MIND MAP (en premier)
```
mind_map = nlm_generate_mind_map(notebook_id)
```
Parser le Mind Map pour extraire :
- `central_concepts` : noeuds avec ≥ 3 connexions (concepts importants)
- `peripheral_concepts` : noeuds avec 1 connexion (concepts secondaires)
- `inter_branch_connections` : liens entre branches différentes (candidats Bridge Notes)
- `concept_hierarchy` : {concept: {parent, children}} pour le frontmatter

Log : "[Mind Map] {N} concepts, {N} central, {N} inter-branch connections"

### 2b. STUDY GUIDE (informe les étapes suivantes)
```
study_guide = nlm_generate_study_guide(notebook_id)
```
Parser le Study Guide :
- Extraire les sections principales → liste de concepts
- Pour chaque concept : noter si présent dans `central_concepts` du Mind Map → Tier S candidate
- Extraire les sous-questions → seront utilisées dans la FAQ et le Q&A ciblé

Appliquer la **détection de tier** :
- Tier S : concept dans `central_concepts` du Mind Map ET ≥ 2 sous-questions non-triviales
- Tier A : concept dans Study Guide avec ≥ 1 sous-question
- Tier B : concept mentionné en 1 seule phrase sans sous-question

### 2c. FAQ
```
faq = nlm_generate_faq(notebook_id)
```
Parser la FAQ :
- Extraire chaque paire Q/R avec sa citation NotebookLM
- Matcher chaque Q/R avec le concept Study Guide correspondant
- Les citations deviennent les entrées `source_chain` du frontmatter

### 2d. DATA TABLE
```
data_table = nlm_generate_data_table(notebook_id)
```
Parser le Data Table :
- Extraire les axes de comparaison (colonnes)
- Pour chaque paire de sources divergeant sur un axe → candidat Bridge Note
- Pour chaque divergence pertinente pour les projets actifs → candidat note `type: decision`

### 2e. BRIEFING DOC
```
briefing_doc = nlm_generate_briefing_doc(notebook_id)
```
Parser le Briefing Doc :
- Détecter les phrases de contradiction ("however", "despite", "in contrast") → candidats `#challenge-assumption`
- Détecter les phrases de consensus ("multiple studies confirm") → note confiance haute
- Extraire le contexte narratif pour enrichir les `## Détail`

### 2f. Q&A CIBLÉ (le vrai différentiateur)

Sélectionner 5-7 questions depuis la bibliothèque ci-dessous selon le domaine et les résultats 2a-2e.
Poser chaque question via le chat NotebookLM et capturer la réponse avec citations.

```
for question in selected_questions:
    answer = nlm_chat(notebook_id, question)
    qa_results.append({question, answer, citations})
```

---

## BIBLIOTHÈQUE DE QUESTIONS Q&A

### Questions universelles (toujours applicables)
1. "What are the 3 most important concepts in this corpus that deserve permanent notes?"
2. "What do these sources collectively NOT cover that represents a significant knowledge gap?"
3. "Which concept here most directly contradicts conventional wisdom in this field?"
4. "If I could only retain one actionable insight from this entire corpus, what would it be and why?"
5. "Explain the most technically complex idea in this corpus as if to a senior web developer who has never worked in this domain."
6. "What practical trade-off is described in these sources that would affect a production deployment?"
7. "What concept here is most likely to be outdated within 12 months?"
8. "Which two concepts from different papers would create the most interesting combined insight?"
9. "What is the minimal viable understanding of [most complex concept] — the 20% that gives 80% of the value?"
10. "Which concept here is the best candidate for a bridge note connecting this domain to another in my vault?"

### Questions domaine AI
1. "How does [central concept from Mind Map] apply to an autonomous agent that processes an inbox with a fixed token budget?"
2. "Which paper here describes a technique to improve cross-reference discovery in a knowledge vault?"
3. "What meta-cognitive capability described here is missing from current LLM-based coding agents?"
4. "Which reinforcement learning technique would best optimize a nightly agent's decision between deep synthesis and broad coverage?"
5. "What safety technique here could prevent a knowledge agent from generating Collector's Fallacy content?"

### Questions domaine Cloud
1. "Which serverless pattern here is most compatible with a Next.js 15 + Vercel deployment?"
2. "What event-driven pattern here would address a race condition between cart clearing and order placement in an e-commerce checkout?"
3. "Which caching strategy here contradicts Next.js 15 default no-store behavior, and what are the performance implications?"
4. "What cost optimization applies to a system with predictable nightly batch workloads?"
5. "Which observability approach works for a multi-script pipeline (3 scheduled scripts + nightly agent)?"

### Questions domaine Ecommerce
1. "Which technique here is most applicable to a B2B auto parts catalog with 50k+ SKUs and compatibility matrices?"
2. "What checkout optimization here addresses the race condition between payment confirmation and inventory update?"
3. "Which fraud detection approach is cost-effective for 10k orders/month on a serverless stack?"
4. "What e-invoicing pattern is compatible with French Factur-X/UBL requirements (deadline Sept 2026)?"
5. "Which personalization approach works without collecting personal data (GDPR-compliant by design)?"

### Questions domaine IoT
1. "Which federated learning approach minimizes bandwidth for battery-powered edge devices reporting to GCP?"
2. "What security pattern addresses IoT device management in a retail/logistics warehouse context?"
3. "How does the digital twin concept here apply to supply chain modeling, not just physical devices?"
4. "Which edge aggregation pattern reduces cloud ingestion costs for high-frequency sensor data?"
5. "What predictive maintenance technique is most applicable to monitoring delivery vehicles or warehouse equipment?"

### Questions topics custom (Firebase, GCP events, etc.)
1. "What limitations in [technology] are NOT documented in the official docs but appear in these sources?"
2. "Which pattern here contradicts the official best practices, and is the contradiction justified?"
3. "How does [technology] integrate with a Next.js 15 Server Actions architecture?"
4. "What is the migration path from the current approach to [technology] for an existing production system?"
5. "Which concept here solves a problem I didn't know I had in my current stack?"

---

## PHASE 3 — Génération des pre-notes

### 3a. Sélection des questions Q&A
Pour chaque domaine, sélectionner 5 questions :
- 2 questions universelles (choisir celles les plus pertinentes selon les résultats 2a-2e)
- 3 questions spécifiques au domaine

### 3b. Fusion des outputs par concept
Pour chaque concept Tier A/S identifié dans Study Guide :

**Construire le draft :**
```
titre = reformuler_en_declaratif(concept.title)  # phrase affirmative testable
essentiel = trouver_faq_matching(concept, faq) ou qa_results[question_feynman]
detail = concept.study_guide_content + briefing_doc_context(concept)
liens = data_table_cross_refs(concept) + mind_map_siblings(concept)
parent = mind_map_hierarchy[concept].parent
children = mind_map_hierarchy[concept].children
```

**Test anti-Collector's Fallacy :**
Avant d'écrire : comparer `essentiel` avec le texte source NotebookLM.
Si les 5 premiers mots sont identiques au texte source → REFORMULER.
Le test : peut-on expliquer l'Essentiel sans regarder la source ? Si non → reformuler.

**Écrire le draft :**
```markdown
---
type: concept
maturity: fleeting
tier: {tier}
created: {date}
source_chain:
  - "origin: {arxiv_url_ou_source_url}"
  - "via: notebooklm-weekly W{week} — domain: {domain}"
notebooklm_meta:
  extraction_method: {study_guide|qa|faq}
  mind_map_position: {central_node|branch|peripheral}
  faq_confidence: {high|medium}
  parent_concept: "{parent_slug}"
  child_concepts: ["{child1}", "{child2}"]
---

# {titre declaratif}

Tags: #{domain} #{tag2}

## Essentiel
{essentiel reformulé — jamais copié}

## Détail
{detail complet reformulé}

## Liens
- [[{lien_existant}]] — {raison du lien}

<!-- generated: {date} | source: notebooklm-weekly -->
```

Nom de fichier : `draft-{slug-du-titre}.md` dans `_inbox/raw/concepts/`

### 3c. Bridge Notes candidates
Pour chaque `inter_branch_connection` du Mind Map ET chaque divergence du Data Table :
Créer `_inbox/review/bridge-draft-{concept-a}-{concept-b}-W{N}.md`

Format :
```markdown
---
type: bridge
maturity: fleeting
tier: A
created: {date}
bridges: ["{concept-a}", "{concept-b}"]
source: "notebooklm-weekly W{N} — {extraction_source}"
---

# {Concept A} et {Concept B} se renforcent mutuellement par {mécanisme}

Tags: #{domain-a} #{domain-b} #bridge

## Essentiel
{POURQUOI ces deux concepts s'éclairent mutuellement — reformulé}

## Liens
- [[{concept-a}]] — concept source
- [[{concept-b}]] — concept cible
```

### 3d. Digest literature (Tier B + synthèse)
Créer `_inbox/raw/digests/notebooklm-digest-{domain}-W{N}.md` :
- Briefing Doc complet (reformulé, pas copié)
- Liste des concepts Tier B (1 phrase chacun)
- Liste des gaps détectés
- Liste des contradictions identifiées

### 3e. Fichiers review
Si des gaps ont été détectés → appender à `_inbox/review/gaps-W{N}.md`
Si des contradictions → appender à `_inbox/review/contradictions-W{N}.md`

---

## PHASE 4 — Mise à jour état et logging

### 4a. Mettre à jour `_meta/notebooklm-state.json`
```json
{
  "notebooks": { "{domain}": "{notebook_id}" },
  "last_sync": { "{domain}": "YYYY-MM-DD" },
  "pushed_papers": { "{domain}": ["arxiv_id1", "arxiv_id2"] }
}
```

### 4b. Écrire `_logs/notebooklm-weekly-W{N}.json`
```json
{
  "run_date": "YYYY-MM-DD",
  "week": N,
  "domains_processed": [],
  "topics_processed": [],
  "papers_pushed": N,
  "concepts_extracted": N,
  "tier_distribution": {"S": N, "A": N, "B": N},
  "bridge_drafts": N,
  "gaps_detected": N,
  "contradictions": N
}
```

### 4c. Rapport terminal
```
✅ Domain: ai     → 5 papers, 8 concepts (S:2 A:4 B:2), 1 bridge draft, 2 gaps
✅ Domain: cloud  → 3 papers, 5 concepts (S:1 A:3 B:1), 0 bridge drafts
⏭ Topic: neural-networks (on-demand, skipped)
⏭ Topic: firebase (insufficient sources: 1/3 minimum)

Pre-notes written: 12 → _inbox/raw/concepts/
Bridge drafts: 1 → _inbox/review/
Ready for nightly agent.
```

---

## SÉQUENCES ADAPTÉES PAR TYPE DE SOURCE

### Papers arXiv (académiques)
Séquence complète : Mind Map → Study Guide → FAQ → Data Table → Briefing Doc → Q&A (5 questions)

### Documentation technique (Firebase, GCP, framework docs)
Séquence allégée : Data Table → FAQ → Q&A (10 questions — plus de Q&A, moins de outputs auto)
Raison : les docs sont déjà structurées, le Mind Map y est redondant. La valeur est dans les questions ciblées sur les limitations non-documentées.

### Articles/blog posts (best practices, retours d'expérience)
Séquence : Mind Map → Briefing Doc → FAQ → Q&A (5 questions)
Raison : le Mind Map révèle les biais de l'auteur. Le Briefing Doc synthétise les perspectives. La FAQ détecte les contradictions avec la documentation officielle.

---

## RÈGLES ABSOLUES

- Ne JAMAIS écrire dans `sensitive.nosync/` ni `_work.nosync/`
- Ne JAMAIS créer de pre-note sans passer le test anti-Collector's Fallacy
- Ne JAMAIS pousser de concepts Tier C dans `_inbox/raw/concepts/`
- Si notebooklm-mcp n'est pas disponible → arrêter proprement (pas de fallback silencieux)
- Chaque pre-note doit avoir un titre déclaratif testable — si impossible → skip le concept
- Maximum 15 pre-notes par run (éviter l'inflation d'inbox)
