# Découverte — Architecture Interne claude-mem

Source: _inbox/session/session-2026-04-10-weekly.md | Vérifié: 2026-04-11 | Confiance: haute
Tags: #second-brain #discovery #claude-mem #sqlite #chromadb #mcp #architecture

## Essentiel
claude-mem utilise SQLite local dans `~/.claude-mem/` — offline, sans dépendance API distante. Daemon background persistant avec HTTP API. ChromaDB opérationnel (`~/.claude-mem/chroma/`, 13 Mo) — embeddings vectoriels disponibles dès le début.

## Détail
- Data dir : `~/.claude-mem/`
- Worker service : `~/.claude/plugins/marketplaces/thedotmack/plugin/scripts/worker-service.cjs`
- ChromaDB : `~/.claude-mem/chroma/` — recherche sémantique disponible sans installation Ollama
- Registration MCP non visible dans `settings.json`, hooks, ni `CLAUDE.md` (mécanisme opaque)
- Hooks Setup + SessionStart injectent le contexte au démarrage (pas PostToolUse seul)
- Supporte recherche cross-projet via paramètre `project`

**À exploiter** : ChromaDB existant = base pour Approach B future (corpus queryable).

## Liens
- [[decision-weekly-extractor-approach-c]]
- [[discovery-claude-mem-privacy-risk]]

<!-- generated: 2026-04-11 -->
