# Second Brain v4 — 5 Gaps Karpathy Audit Corrigés

Source: _inbox/session/session-2026-04-11.md | Vérifié: 2026-04-12 | Confiance: haute
Tags: #second-brain #architecture #karpathy #audit #v4 #discovery

## Essentiel
Audit Karpathy de v3 a révélé 5 manques structurels → tous corrigés dans v4 (PR#6).
La v4 est validée : anti-re-ingestion testée (second run → notes_added: 0), 25 notes actives.

## Détail

| Gap | Problème v3 | Fix v4 |
|-----|-------------|--------|
| 1 — Raw input layer | Aucune zone pour articles externes | `_inbox/raw/articles/`, `docs/`, `repos/` |
| 2 — Anti-re-ingestion | Re-ingestion possible à chaque run | `_meta/LOG.md` append-only, vérification avant traitement |
| 3 — Lint | Orphelines, wikilinks cassés jamais détectés | Étape 4 nightly → `_logs/maintenance-report.md` |
| 4 — Cross-références | Nouvelles notes jamais liées aux existantes | Étape 3 nightly, max 5 updates/run, tags communs |
| 5 — Quarantine | Workflow `_inbox/agent/` jamais implémenté | Supprimé, filing direct vers `universal/` ou `projects/` |

Forces Karpathy conservées : INDEX.md navigation, notes atomiques Source: traceability, wikilinks graphe implicite, Light Mode (0 WebSearch).

## Liens
- [[discovery-vault-failles-audit]]
- [[decision-knowledge-graph-deferred]]
- [[discovery-nightly-agent-architecture]]

<!-- generated: 2026-04-12 -->
