# Décision — Weekly Extractor : Approach C (session interactive)

Source: _inbox/session/session-2026-04-10-weekly.md | Vérifié: 2026-04-11 | Confiance: haute
Tags: #second-brain #decision #weekly-extractor #claude-mem #architecture

## Essentiel
Architecture choisie : le weekly extractor est une session Claude interactive (pas HTTP worker ni corpus rebuild). Il interroge claude-mem via MCP, filtre les observations, synthétise en note vault `_inbox/session/session-YYYY-MM-DD-weekly.md`, met à jour `_logs/conversations-processed.json`.

## Détail
- Options rejetées : Approach A (algo pur = trop rigide), Approach B (corpus rebuild = tech debt documenté)
- **Approach C validée** : MCP tools disponibles en session interactive, coût nul (Max subscription), pas de dépendance externe
- Premier run réussi (2026-04-10) : 350 obs scannées, 14 exclues privacy, 45 concepts extraits
- PR#4 : Nostaflex/second-brain

Fichiers clés :
- Script : `scripts/weekly-extractor.sh`
- Prompt : `scripts/weekly-extractor-prompt.md`
- State : `_logs/conversations-processed.json`

**Raison technique** : `claude --print` n'initialise pas le plugin system → MCP tools claude-mem inaccessibles en mode non-interactif.

## Liens
- [[discovery-mcp-tools-print-mode]] — contrainte technique fondamentale qui a dicté ce choix
- [[discovery-claude-mem-architecture]] — couche claude-mem requêtée par ce weekly extractor
- [[feature-weekly-extractor-first-run]] — implémentation effective de cette décision, 45 concepts au premier run

<!-- generated: 2026-04-11 -->
