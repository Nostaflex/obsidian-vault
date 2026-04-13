---
status: future-implementation
priority: medium
created: 2026-04-13
tags: [future, mcp, obsidian, integration]
domain: second-brain
type: implementation-idea
---

# MCP Obsidian Server (MarkusPfundstein) — Future Implementation

> **Status** — 🔮 À installer dans une session dédiée (~30 min). Pas urgent — les Read/Edit natifs marchent déjà via permissions.

## Contexte

Décision audit du 2026-04-13 : remplacer le MCP `obsidian-vault` cassé (pointait vers tmpdir mort `/var/folders/.../tmp.hdWpzdR59A/`) par [obsidian-mcp-server](https://github.com/MarkusPfundstein/mcp-obsidian) (3k+ stars, full read/write/search/tag).

L'ancien MCP a été retiré aujourd'hui (`~/.claude/mcp.json` vidé). Les opérations sur le vault passent désormais par les outils Read/Edit natifs de Claude Code via les permissions globales.

## Pourquoi installer ce MCP

Avantages d'un MCP Obsidian dédié vs Read/Edit natifs :

| Capabilité | Read/Edit natif | obsidian-mcp-server |
|------------|-----------------|---------------------|
| Lire/écrire fichier | ✅ | ✅ |
| Search par tag Obsidian | ❌ | ✅ |
| Search dataview queries | ❌ | ✅ |
| Lister backlinks | ❌ | ✅ |
| Création note avec template | manuel | ✅ via API |
| Compatible mode liens [[wiki]] | manuel | ✅ natif |
| Performance scan vault | parsing maison | indexé Obsidian |

→ Particulièrement utile pour les workflows "trouver tous les concepts orphelins" ou "lister les notes avec tag #ai créées cette semaine".

## Prérequis

1. **Obsidian doit tourner** sur le Mac (l'API REST est exposée par un plugin)
2. **Plugin Community "Local REST API"** installé dans Obsidian
3. **API key** générée par ce plugin
4. **Node.js** ≥ 18 (déjà présent vu les usages npx)

## Plan d'installation

### Étape 1 — Plugin Obsidian
1. Ouvrir Obsidian → Settings → Community Plugins → Browse
2. Chercher "Local REST API" → Install + Enable
3. Settings du plugin :
   - HTTPS port : 27124 (par défaut)
   - Insecure HTTP : OFF (sécurité)
   - Generate API key → **noter la clé**

### Étape 2 — Stockage API key dans Keychain
```zsh
security add-generic-password -U -a djemildavid -s obsidian-rest-api -w '<api_key_obsidian>'
```

### Étape 3 — Installation du serveur MCP

Option A — npm global :
```zsh
npm install -g @modelcontextprotocol/obsidian-server
# OU si MarkusPfundstein :
npm install -g obsidian-mcp-server
```

Option B — uvx (Python wrapper, plus léger) :
```zsh
uvx install obsidian-mcp-server  # selon le packaging upstream
```

### Étape 4 — Configuration `~/.claude/mcp.json`
```json
{
  "mcpServers": {
    "obsidian": {
      "command": "obsidian-mcp-server",
      "env": {
        "OBSIDIAN_API_KEY": "$(security find-generic-password -a djemildavid -s obsidian-rest-api -w)",
        "OBSIDIAN_HOST": "https://127.0.0.1:27124"
      }
    }
  }
}
```

> ⚠️ Note : la résolution de `$(...)` dans `mcp.json` peut ne pas marcher selon Claude Code. Tester. Si KO, créer un wrapper script :
>
> ```zsh
> #!/usr/bin/env zsh
> # ~/.local/bin/obsidian-mcp-launcher.sh
> export OBSIDIAN_API_KEY="$(security find-generic-password -a djemildavid -s obsidian-rest-api -w)"
> export OBSIDIAN_HOST="https://127.0.0.1:27124"
> exec obsidian-mcp-server "$@"
> ```
> Puis dans mcp.json : `"command": "/Users/djemildavid/.local/bin/obsidian-mcp-launcher.sh"`

### Étape 5 — Vérifier
1. Redémarrer Claude Code
2. Vérifier que les outils `mcp__obsidian__*` apparaissent
3. Test : `mcp__obsidian__list_files_in_vault()` → doit retourner les fichiers du vault

## Points d'attention

- **Auth** : éviter HTTPS auto-signé en pluraint le warning curl/node, ou installer le certificat self-signed
- **Conflit ports** : port 27124 — vérifier qu'il n'est pas occupé (`lsof -i :27124`)
- **Sécurité** : seul localhost a accès — ne JAMAIS exposer publiquement
- **Sync iCloud** : si Obsidian sync iCloud est actif, attendre que la sync soit complète avant les ops MCP

## Use cases concrets pour le Second Brain

Une fois installé, ces workflows deviennent triviaux :
- Listing de tous les drafts dans `_inbox/` avec date de création
- Recherche par tag pour audit qualité (`#ai #challenge-assumption` sur la dernière semaine)
- Backlinks d'un concept (qui pointe vers `concept-X`?)
- Génération auto de l'INDEX.md depuis les fichiers actuels
- Quick add de concept depuis script Python via API REST

## Estimation effort

- Setup initial : **30-45 min** (install plugin + npm + config + tests)
- Migration des workflows existants : **0** (additif, pas de migration)
- ROI : **moyen** — utile mais pas urgent. Les Read/Edit natifs couvrent 80% des cas.

## Quand attaquer cela

✅ Quand tu auras un workflow récurrent qui galère avec Read/Edit (ex: "tag-based search", "backlinks discovery")
❌ Pas avant — c'est nice-to-have, pas critique

## Liens internes
- [[audit-setup-claude-code-2026-04-13]] — audit source qui a recommandé ce MCP
- [[tech-debt-registry]] TD-2026-005 — résolution du MCP cassé
- [[future-managed-agents-anthropic]] — autre future implementation

## Tags
#future-implementation #mcp #obsidian #not-urgent
