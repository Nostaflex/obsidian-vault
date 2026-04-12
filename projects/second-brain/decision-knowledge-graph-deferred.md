# Knowledge Graph — Route différée (Second Brain)

Source: session-2026-04-10 — audit Karpathy complet | Vérifié: 2026-04-10 | Confiance: haute
Tags: #second-brain #architecture #decision #graph #karpathy #futur

## Essentiel

Ajouter un knowledge graph sur le vault a été évalué et **différé délibérément**.
Verdict Karpathy : les wikilinks sont déjà un graphe implicite. Obsidian le rend.
Seuil de pertinence : 100-200 notes minimum. Aujourd'hui on en est à ~3.
Route à reconsidérer quand le vault dépasse 100 notes ET que les queries cross-notes deviennent complexes.

## Pourquoi c'est différé (pas abandonné)

**Ce qu'un graph apporterait :**
- Typed relationships explicites : `uses`, `depends-on`, `contradicts`, `caused`, `fixed`
- Traversal de graph pour des queries relationnelles complexes
- Détection de contradictions automatique sans lint LLM
- Visualisation des dépendances inter-projets (gpparts ↔ second-brain ↔ mind-free)

**Pourquoi pas maintenant :**
- Karpathy lui-même n'utilise pas de graph — wikilinks suffisent à son échelle (~100 articles)
- Pebblous : typed KG = $10M-20M en enterprise, 27% taux de succès en prod
- Epsilla : graph justifié par sécurité, gouvernance, millions de docs — pas par organisation des connaissances
- Maintenance overhead > bénéfice à < 100 notes
- Schéma typé devient stale quand les concepts évoluent

**Ce qu'on a déjà qui est un graph :**
Les `[[wikilinks]]` dans les notes sont des edges. Obsidian Graph View les rend visuellement.
Le Step 3 cross-références (nightly v4) tisse ce graphe automatiquement à chaque ingest.
Le Step 4 lint détecte les nodes orphelins et les contradictions textuelles.

## Conditions de déclenchement

Reconsidérer cette route si **au moins 2 des 3 conditions** sont réunies :

1. **Volume :** vault dépasse 100 notes actives dans `universal/` + `projects/`
2. **Query complexity :** queries du type "toutes les décisions causées par X" ou "quels projets dépendent de Y" deviennent fréquentes
3. **Contradiction rate :** le lint identifie > 5 contradictions non résolues sur un mois

## Route d'implémentation suggérée (si déclenchée)

### Phase 1 — Typed annotations inline (0 infrastructure)

Étendre le template de note avec 2 champs optionnels :

```markdown
Remplace: [[ancienne-note]]         # déjà dans VAULT.md
Contradits: [[note-opposée]]        # NOUVEAU
Requis-par: [[note-dépendante]]     # NOUVEAU
```

Grep-able par `integrity-check.sh`. Nativement lisible par Claude et Djemil.
Coût : modification d'une ligne dans VAULT.md + prompt nightly. Zéro tooling.

### Phase 2 — Graph extraction légère (si Phase 1 insuffisante)

Utiliser `qmd` (recommandé par Karpathy) ou `llm-wiki-compiler` (ussumant/llm-wiki-compiler sur GitHub).
Ces outils lisent le vault markdown et produisent un index de relations sans modifier les fichiers sources.
MCP integration possible pour exposer le graph traversal à Claude.

### Phase 3 — Graph structurel complet (si Phase 2 insuffisante)

LLM Wiki v2 pattern (rohitg00/agentmemory) :
- Entity extraction avec types (people, projects, libraries, decisions)
- Typed relationships + graph traversal
- Hybrid search : BM25 + embeddings + graph
Seuil réaliste : 200+ notes actives, queries inter-projets fréquentes.

## Sources ayant informé cette décision

- [Karpathy llm-wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — pas de graph, wikilinks suffisent
- [LLM Wiki v2](https://gist.github.com/rohitg00/2067ab416f7bbe447c1977edaaa681e2) — graph utile au-delà de 100-200 notes
- [Epsilla enterprise graph](https://www.epsilla.com/blogs/llm-wiki-kills-rag-karpathy-enterprise-semantic-graph) — graph = sécurité/gouvernance/millions de docs
- [Pebblous — ontology vs wikilinks](https://blog.pebblous.ai/report/karpathy-llm-wiki/en/) — graph harms at intimate scale

## Liens
- [[architecture-dual-profile-vscode]]
- [[decision-architecture-hybride-second-brain]]
- [[discovery-vault-failles-audit]]
- [[discovery-second-brain-v4-gaps-fixes]]

<!-- generated: 2026-04-10 -->
