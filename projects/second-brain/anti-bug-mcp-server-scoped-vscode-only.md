---
type: anti-bug
maturity: fleeting
tier: A
created: 2026-04-12
source_chain:
  - "origin: _inbox/session/session-2026-04-11-weekly.md"
  - "via: claude-mem obs #517 / #203"
---

# Un serveur MCP dans settings.json peut être scopé à VS Code uniquement — les scripts launchd y auront zéro accès

Tags: #second-brain #anti-bug #mcp #vscode #launchd #scope #configuration

## Essentiel
Les serveurs MCP configurés dans `~/.claude/settings.json` sous `mcpServers` sont actifs uniquement dans l'environnement qui charge ce fichier. Un script lancé par launchd (hors VS Code) ne bénéficie pas de cette configuration et échoue silencieusement.

## Détail
Découverte lors de la validation du pipeline enrichissement : le serveur MCP `knowledge-base` n'était accessible que depuis VS Code. Un agent nocturne launchd qui suppose l'accès MCP global requêtait silencieusement le vide. Diagnostic : vérifier dans quel contexte `~/.claude/settings.json` est lu (IDE vs CLI vs launchd). Solution systémique : ne jamais compter sur les MCP dans les pipelines launchd, confiner les intégrations MCP aux sessions interactives. Complète la découverte `claude --print` = sans MCP.

## Liens
- [[discovery-mcp-tools-print-mode]] — contrainte identique mais depuis le flag --print (complémentaire)
- [[anti-bug-launchd-icloud-tcc]] — autre catégorie de bugs launchd lié aux contextes d'exécution réduits

<!-- generated: 2026-04-12 -->
