# Découverte — MCP Tools inaccessibles en mode --print

Source: _inbox/session/session-2026-04-10-weekly.md | Vérifié: 2026-04-11 | Confiance: haute
Tags: #second-brain #discovery #claude-cli #mcp #nightly-agent #print-mode

## Essentiel
`claude --print` (mode non-interactif utilisé par le nightly agent) n'initialise pas le plugin system → MCP tools inaccessibles. L'intégration claude-mem dans le nightly agent est donc **techniquement bloquée**. C'est la raison fondamentale du choix du weekly extractor en session interactive (Approach C).

## Détail
- Découverte critique lors de l'audit architecture du 2026-04-10
- `mcp__plugin_claude-mem_mcp-search__*` non appelable depuis `--print`
- Alternative validée : weekly extractor = session Claude interactive
- Tech debt documenté : Approach B (corpus queryable via HTTP)

Impact sur architecture : toute intégration claude-mem doit passer par une session interactive, pas par `nightly-agent.sh`.

## Liens
- [[decision-weekly-extractor-approach-c]] — décision architecturale qui découle directement de cette contrainte
- [[discovery-nightly-agent-architecture]] — contexte du pipeline nocturne impacté par cette limite
- [[anti-bug-mcp-server-scoped-vscode-only]] — contrainte complémentaire: MCP scopé VS Code, invisible aux scripts launchd

<!-- generated: 2026-04-11 -->
