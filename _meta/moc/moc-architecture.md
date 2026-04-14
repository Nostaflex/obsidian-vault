---
type: moc
tag: architecture
notes_count: 14
last_updated: 2026-04-15
scope: "auto-generated MOC for tag #architecture"
---
# MOC — #architecture
Generated: 2026-04-15 | 14 notes

- [[architecture-dual-profile-vscode]] — Deux profils VSCode séparés avec LLM et accès vault distincts : Personal
- [[architecture-token-efficient-skills]] — ADR — Design token-efficient pour les skills custom
- [[decision-architecture-hybride-second-brain]] — Architecture hybride Algo+LLM choisie : injection directe vault (pas de tier staging),
- [[decision-bash-vs-python-boundary]] — ADR — Frontière Bash vs Python dans le Second Brain Pipeline
- [[decision-knowledge-graph-deferred]] — Ajouter un knowledge graph sur le vault a été évalué et différé
- [[decision-vault-seed-runtime-pattern]] — Le repo git contient vault/ (source de vérité pour l'initialisation). Le vault
- [[decision-weekly-extractor-approach-c]] — Architecture choisie : le weekly extractor est une session Claude interactive (pas
- [[discovery-claude-mem-architecture]] — claude-mem utilise SQLite local dans ~/.claude-mem/ — offline, sans dépendance API distante.
- [[discovery-nightly-agent-architecture]] — launchd cron à 2h17 → nightly-agent.sh → claude --print .nightly-prompt.md → notes
- [[discovery-second-brain-v4-gaps-fixes]] — Audit Karpathy de v3 a révélé 5 manques structurels → tous corrigés
- [[discovery-vault-failles-audit]] — Audit du 2026-04-10 : 4 failles structurelles identifiées dans le vault. Prochaine
- [[feature-enrichment-pipeline-approach-b]] — L'enrichissement du vault suit l'Approche B : le nightly agent consulte meta/watchlist.md
- [[meta-purpose-lab-for-enterprise]] — Ce vault a 3 missions simultanées et explicites : 1. Lab de
- [[pattern-inbox-raw-layer]] — Le vault v4 dispose d'une zone de dépôt pour les sources externes
