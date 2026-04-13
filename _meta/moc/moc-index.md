---
type: moc
scope: "Master index of all MOCs — routing table for /load-moc skill"
notes_count: 0
last_updated: 2026-04-13
generated_by: manual (will be overridden by nightly)
---

# MOC — Master Index

> **Routing table** pour `/load-moc <topic>` — charge le MOC approprié selon le scope.

## MOCs thématiques

| MOC | Scope | Notes | Quand l'utiliser |
|-----|-------|-------|------------------|
| [[moc-second-brain]] | Principal cross-domain | 27 | Entry point principal — si doute |
| [[moc-architecture]] | Décisions architecture, patterns, pipeline | 12 | Questions "comment c'est conçu / pourquoi ce choix" |
| [[moc-decision]] | ADRs uniquement | — | Rappel d'une décision passée précise |
| [[moc-discovery]] | Findings / learnings | — | "Qu'est-ce qu'on a appris sur X ?" |
| [[moc-anti-bug]] | Bugs résolus + patterns d'évitement | — | Debug, prévention régression |
| [[moc-nightly-agent]] | Pipeline nocturne (launchd, corpus, synth) | 5 | Questions sur cron, nightly-agent.sh |
| [[moc-security]] | Sécurité, secrets, permissions, audits | — | Audit sécurité, gestion keychain |
| [[moc-gpparts]] | Projet annexe GPParts | — | Si projet GPParts (pas Second Brain) |

## Règles de routing

1. **Exact match** : si `<topic>` contient un tag de la colonne Scope → charger ce MOC direct
2. **Multi-MOC** : si topic croise 2 scopes (ex: "crash nightly" = anti-bug + nightly-agent) → charger les 2
3. **Ambigu** : si pas de match clair → charger `moc-second-brain.md` (master cross-domain)
4. **Hors-vault** : si la query est sur de l'historique de sessions → invoke `mcp__claude-mem__search` à la place

## Auto-generation

Ce fichier est **régénéré chaque nuit** par `.nightly-prompt.md` après mise à jour des MOCs.
Modifications manuelles de la section "MOCs thématiques" seront écrasées.

## Tags
#meta #moc #routing
