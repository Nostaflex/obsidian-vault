# Knowledge Base — Règles et conventions

## Structure des dossiers

- `universal/` — Notes applicables à 2+ projets
- `projects/{projet}/` — Notes spécifiques à 1 projet
- `_inbox/session/` — Notes de session Claude (input nightly)
- `_inbox/raw/articles|docs|repos/` — Contenu externe brut (input nightly)
- `_inbox/raw/papers/{domain}/` — Papers scientifiques collectés par corpus_collector.py
- `_inbox/raw/concepts/` — Pre-notes atomiques générées par paper_synthesizer.py
- `_inbox/review/` — Files en attente de revue humaine (bridge notes draft, weekly review)
- `_meta/` — INDEX, context-cards, MOC, LOG, signals
- `_logs/` — Logs opérationnels (last-nightly.json, maintenance-report, broken-links)
- `_archive/` — Notes archivées (maturity: archive-candidate depuis 30+ jours)

## Règle de filing

**universal/** : applicable à 2+ projets (ex: pattern technique, convention transversale)
**projects/{projet}/** : spécifique à 1 projet

Auditer avant de créer : si un concept concerne gpparts ET second-brain → universal/

## Types de notes (champ `type` dans le frontmatter)

| type | Description |
|------|-------------|
| `concept` | Idée, principe, concept technique |
| `decision` | Décision d'architecture ou de design |
| `pattern` | Pattern réutilisable |
| `discovery` | Découverte, observation |
| `anti-bug` | Anti-pattern, bug connu à éviter |
| `bridge` | Note de pont — explique POURQUOI deux concepts sont liés |
| `literature` | Synthèse d'une source externe (digest, paper) |

## Niveaux de maturité (champ `maturity`)

| maturity | Signification |
|----------|--------------|
| `fleeting` | Créé par l'agent — non validé par Djemil. Durée de vie < 14 jours avant review. |
| `literature` | Validé par Djemil. Reformulé, ancré dans une source. |
| `evergreen` | Note permanente. Autonome, décontextualisée, titre déclaratif fort. |
| `archive-candidate` | Signalé par le lint. 0 backlinks depuis 30+ jours. |

**Règle critique : seul Djemil promeut une note. L'agent crée toujours `fleeting`.**

## Tier List (champ `tier`)

| tier | Critère |
|------|---------|
| `S` | Directement applicable à un projet actif. Traitement complet. |
| `A` | Concept solide à valeur future. Note atomique complète. |
| `B` | Référence intéressante. Essentiel court (1 phrase). |

## Template de note atomique

```yaml
---
type: concept
maturity: fleeting
tier: A
created: YYYY-MM-DD
source_chain:
  - "origin: URL ou chemin source primaire"
  - "via: chemin intermédiaire (digest, session)"
---

# [Titre déclaratif — phrase affirmative testable]

Tags: #tag1 #tag2

## Essentiel
[2-3 lignes max. Reformulé, jamais copié-collé.]

## Détail
[Contenu complet reformulé.]

## Liens
- [[note-existante]] — raison du lien en 1 phrase

<!-- generated: YYYY-MM-DD -->
```

## Conventions de nommage

- Noms de fichiers : kebab-case, descriptifs, préfixe type quand utile
  - `decision-{nom}.md` — pas de sous-dossier decisions/
  - `anti-bug-{nom}.md`
  - `pattern-{nom}.md`
  - `discovery-{nom}.md`
  - `bridge-{concept-a}-{concept-b}.md`
- Wikilinks : Obsidian résout par **basename** (sans chemin)
- Éviter les sous-dossiers dans projects/ (ex: `decisions/`) — ça casse les wikilinks

## Agents automatisés

- **Nightly agent** : tourne à 2h17 via launchd. Traite _inbox/session/ + _inbox/raw/
- **corpus_collector.py** : hebdomadaire (samedi). Collecte papers arXiv + Semantic Scholar.
- **paper_synthesizer.py** : hebdomadaire (dimanche). Gemini API → pre-notes atomiques dans _inbox/raw/concepts/

## Projets actifs

- **gpparts** : plateforme e-commerce pièces auto (Next.js 15)
- **second-brain** : ce vault lui-même

## Zones interdites

- `sensitive.nosync/` et `_work.nosync/` — jamais toucher
