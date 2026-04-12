---
type: concept
maturity: fleeting
tier: A
created: 2026-04-12
source_chain:
  - "origin: docs/pkm/art-mytose-preserver-contexte"
  - "via: _inbox/raw/docs/art-mytose-preserver-contexte-atomique.md"
---

# La section ## Liens avec annotation obligatoire est le mécanisme de préservation du contexte après mitose cognitive

Tags: #pkm #second-brain #context-preservation #wikilinks #cognitive-mitosis #note-taking

## Essentiel
Après une mitose cognitive, les notes résultantes perdent leur contexte d'origine si les liens entre elles ne sont pas annotés. Un lien nu `[[note]]` ne dit pas pourquoi les deux concepts se touchent — c'est l'annotation `— raison` qui préserve ce contexte.

## Détail
La règle d'annotation obligatoire dans ce vault (`[[note]] — raison du lien en 1 phrase`) n'est pas stylistique. Elle répond à un problème structurel : lors d'une mitose sur une source de 4 concepts, le lecteur futur (Djemil dans 6 mois) n'a aucun moyen de reconstruire pourquoi ces notes étaient ensemble si les liens sont nus. L'annotation encode le pont sémantique. Concrètement, l'annotation doit répondre à : « Pourquoi est-ce que je pointe vers cette note depuis ici ? ». Le type `bridge` est l'extension de ce principe aux connexions cross-domaines fortes : une note entièrement dédiée à expliquer pourquoi deux concepts de domaines différents s'éclairent mutuellement. Le workflow Claude applique ce principe à deux niveaux : annotations dans `## Liens` (niveau note) et `bridge-draft-{a}-{b}.md` dans `_inbox/review/` (niveau macro-connexion).

## Liens
- [[concept-cognitive-mitosis-atomicity]] — le contexte à préserver est justement produit par la mitose
- [[concept-collectors-fallacy-accumulation-passive]] — un lien sans annotation reproduit la Collector's Fallacy au niveau des liens

<!-- generated: 2026-04-12 -->
