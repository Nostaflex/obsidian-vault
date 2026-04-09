# Knowledge Base — Règles et conventions

## Template de note (obligatoire)

```markdown
# Titre du concept (une seule idée)

Source: [nom ou URL] | Vérifié: YYYY-MM-DD | Confiance: haute/moyenne/basse
Tags: #tag1 #tag2 #tag3

## Essentiel

[Ce qu'il faut savoir en 3 lignes max — lu en priorité par Claude, ~50 tokens]

## Détail

[Explication complète, exemples, code si pertinent]

## Liens

- [[note-cible-confirmée-dans-INDEX]]

<!-- generated: YYYY-MM-DD -->
```

## Règle d'atomicité (Zettelkasten)

1 note = 1 concept testable indépendamment.
Test : peut-on supprimer une section sans que le reste soit incomplet ?
Si oui → deux notes distinctes.

## Règle des wikilinks (write-time)

Un `[[lien]]` n'est écrit que si la note cible est confirmée dans INDEX.md
au moment de l'écriture. Sinon → texte simple sans brackets.
Raison : les LLMs génèrent des liens vers des notes inexistantes (Karpathy 2025).

## Niveaux de confiance

- **haute** — documentation officielle OU consensus ≥3 sources → `_inbox/agent/`
- **moyenne** — source reconnue, consensus partiel → `_inbox/agent/`
- **basse** — journalistique, signal faible → `_inbox/review/` (validation manuelle)

## Quarantine et promotion

Toutes les notes nocturnes → `_inbox/agent/YYYY-MM-DD/`
Promotion automatique après **72h sans rejet** (approbation silencieuse).
Validation explicite : ajouter `#validated` dans Obsidian → Auto Note Mover déplace.
Notes marquées `[A]` dans les context-cards = agent pending.

## Arbre de décision filing (déterministe)

```
Est-ce vrai indépendamment du projet ?
  └─ OUI → universal/
  └─ NON → projects/<projet>/

Référence du code spécifique au projet ?
  └─ OUI → projects/<projet>/

Décision d'architecture (ADR) ?
  └─ OUI → projects/<projet>/decisions/
```

## Convention succession (remplacement de note)

Ajouter dans la note remplaçante :
`Remplace: [[ancienne-note]]`
Déplacer l'ancienne vers `_inbox/review/superseded/`.

## Accès vault (Claude)

Claude accède via **`Read` tool natif** aux dossiers `universal/`, `projects/`, `_meta/`.
Le MCP `obsidian-vault` est sandboxé au workspace VS Code — ne pas l'utiliser pour le vault.

Exclus : `sensitive.nosync/`, `_inbox/`, `_logs/`, `_archive/`

## Règles absolues (agent nocturne)

- Ne jamais toucher à `sensitive/`
- Ne jamais écrire directement dans `universal/` ou `projects/`
- Toujours passer par `_inbox/agent/` (quarantine)
- Filtrer tokens, clés API, URLs privées avant tout écrit
- Vérifier wikilinks contre INDEX.md avant écriture
