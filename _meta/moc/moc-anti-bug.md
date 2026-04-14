---
type: moc
tag: anti-bug
notes_count: 7
last_updated: 2026-04-15
scope: "auto-generated MOC for tag #anti-bug"
---
# MOC — #anti-bug
Generated: 2026-04-15 | 7 notes

- [[anti-bug-claude-cli-keychain-launchd]] — Les credentials Claude (OAuth via claude.ai/Max) sont dans login.keychain-db, verrouillé hors sessio
- [[anti-bug-claude-jsonl-schema]] — Les conversations Claude sont dans ~/.claude/projects/ avec répertoires path-encodés. Anti-bug criti
- [[anti-bug-grep-confidentiel-faux-positif]] — Dans integrity-check.sh, le pattern grep "confidentiel" matche le titre H1 d'une section
- [[anti-bug-launchd-icloud-tcc]] — macOS bloque l'accès de launchd à iCloud Drive via TCC. SessionCreate=true dans
- [[anti-bug-mcp-server-scoped-vscode-only]] — Les serveurs MCP configurés dans ~/.claude/settings.json sous mcpServers sont actifs uniquement dans
- [[anti-bug-set-e-jq-missing-file]] — Un script bash avec set -euo pipefail s'arrête immédiatement si jq lit
- [[anti-bug-zip-executable-bit-lost]] — Un fichier .sh extrait d'une archive ZIP n'est exécutable que si chmod
