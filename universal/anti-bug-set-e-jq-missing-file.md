---
type: anti-bug
maturity: fleeting
tier: A
created: 2026-04-12
source_chain:
  - "origin: _inbox/session/session-2026-04-11-weekly.md"
  - "via: claude-mem obs #616 / #617"
---

# Sous set -euo pipefail, jq sur un fichier inexistant fait quitter le script avant toute logique de première exécution

Tags: #anti-bug #bash #set-e #jq #shell #guard

## Essentiel
Un script bash avec `set -euo pipefail` s'arrête immédiatement si `jq` lit un fichier absent. La logique de création de ce fichier (première exécution) n'est jamais atteinte. Il faut tester l'existence avant tout appel `jq`.

## Détail
Bug découvert dans `scripts/nightly-agent.sh` : le guard "déjà exécuté aujourd'hui" appelait `jq -r '.last_run' "$STATE_FILE"` sans vérifier que `$STATE_FILE` existait. Sous `set -e`, le code de sortie non-nul de `jq` termine le script. Correction : `LAST_RUN=$([ -f "$STATE_FILE" ] && jq -r '.last_run // empty' "$STATE_FILE" 2>/dev/null || echo "")`. Le `// empty` de jq retourne une chaîne vide plutôt que `null`, et `2>/dev/null || echo ""` absorbe les erreurs résiduelles. Ce pattern s'applique à tout state file optionnel dans les scripts de pipeline.

## Liens

<!-- generated: 2026-04-12 -->
