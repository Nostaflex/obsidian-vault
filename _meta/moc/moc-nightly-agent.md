---
type: moc
tag: nightly-agent
notes_count: 5
last_updated: 2026-04-15
scope: "auto-generated MOC for tag #nightly-agent"
---
# MOC — #nightly-agent
Generated: 2026-04-15 | 5 notes

- [[convention-log-anti-re-ingestion]] — meta/LOG.md est un registre append-only qui empêche la re-ingestion des fichiers déjà
- [[discovery-mcp-tools-print-mode]] — claude --print (mode non-interactif utilisé par le nightly agent) n'initialise pas le
- [[discovery-nightly-agent-architecture]] — launchd cron à 2h17 → nightly-agent.sh → claude --print .nightly-prompt.md → notes
- [[discovery-nightly-vault-api-transit]] — nightly-agent.sh concatène le contenu des fichiers vault et le transmet à claude
- [[guardrail-nightly-prompt]] — Le guardrail interdisant la lecture de work.nosync/ est textuel (prompt), pas une
