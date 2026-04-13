# Convention — MCP VSCode : Fichier mcp.json Dédié (pas settings.json)

Source: _inbox/session/session-2026-04-10.md | Vérifié: 2026-04-11 | Confiance: haute
Tags: #vscode #mcp #convention #configuration #copilot

## Essentiel
VSCode refuse la configuration MCP dans `settings.json` depuis une version récente. Utiliser `Cmd+Shift+P` → "Preferences: Open User MCP Configuration (JSON)" pour le fichier MCP dédié. Format différent du format Claude.

## Détail
**Format correct pour VSCode mcp.json :**
```json
{
  "servers": {
    "nom-serveur": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/chemin/1", "/chemin/2"]
    }
  }
}
```

**Différence clé** : clé `servers` (pas `mcpServers` comme dans Claude settings.json).

**Anti-bug** : chaque profil VSCode a son propre `mcp.json` — les configs sont isolées par profil. `obsidian-vault` MCP est sandboxé au contexte VS Code — inaccessible depuis Claude CLI natif.

## Liens

<!-- generated: 2026-04-11 -->
