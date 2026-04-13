# Décision — Pattern Vault Seed / Runtime

Source: _inbox/session/session-2026-04-10.md | Vérifié: 2026-04-11 | Confiance: haute
Tags: #second-brain #decision #architecture #vault #setup

## Essentiel
Le repo git contient `vault/` (source de vérité pour l'initialisation). Le vault runtime `~/Documents/Obsidian/KnowledgeBase/` évolue dynamiquement et n'est jamais versionné. `setup.sh --update` propage les changements du seed vers le runtime — jamais l'inverse.

## Détail
**Règle absolue** : toujours modifier `vault/` dans le repo EN PREMIER, puis propager via `scripts/setup.sh --update`.

**Anti-bug critique** : si on édite le runtime directement PUIS on run `setup.sh --update`, le fichier runtime est écrasé par la version seed → perte des modifications. Ordre obligatoire :
1. Modifier `vault/` (seed)
2. `setup.sh --update` (propagation)

Fichiers propagés : templates, `.nightly-prompt.md`, `VAULT.md`, `conversations-processed.json` (seed).

## Liens
- [[discovery-nightly-agent-architecture]]
- [[discovery-vault-failles-audit]]

<!-- generated: 2026-04-11 -->
