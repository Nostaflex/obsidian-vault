# Convention — LOG.md Append-Only Anti-Re-Ingestion

Source: _inbox/session/session-2026-04-11.md | Vérifié: 2026-04-12 | Confiance: haute
Tags: #second-brain #convention #log #anti-re-ingestion #nightly-agent #append-only

## Essentiel
`_meta/LOG.md` est un registre append-only qui empêche la re-ingestion des fichiers déjà traités.
L'agent vérifie le nom du fichier source dans LOG.md avant tout traitement — si trouvé → skip immédiat.

## Détail

**Règle absolue** : ne jamais effacer ni modifier des entrées existantes dans LOG.md.

**Format des entrées** :
```
## [YYYY-MM-DD] ingest | nomfichier.md → N notes
## [YYYY-MM-DD] lint | orphelines: N | contradictions: N | candidats-archivage: N
## [YYYY-MM-DD] extract | weekly session-XXX.md → N concepts extraits
```

**Pourquoi cette règle** : sans LOG.md, chaque run nocturne risquait de re-ingérer les mêmes fichiers inbox → doublons dans le vault, pollution des notes. Ce fix est le Gap 2 de l'audit Karpathy v4.

**Anti-pattern à éviter** : consulter uniquement l'existence physique du fichier dans `_processed/` n'est pas suffisant — le nom peut différer après horodatage. Le grep dans LOG.md est la source de vérité.

## Liens
- [[discovery-second-brain-v4-gaps-fixes]]
- [[discovery-nightly-agent-architecture]]

<!-- generated: 2026-04-12 -->
