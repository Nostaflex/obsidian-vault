#!/bin/bash
# corpus-rebuild.sh — Reconstruit le corpus claude-mem "research-papers"
# Usage : bash corpus-rebuild.sh
# Prérequis : claude CLI installé, claude-mem plugin actif
set -euo pipefail

VAULT="$HOME/Documents/Obsidian/KnowledgeBase"
LOG="$VAULT/_logs/corpus-rebuild.log"
PAPERS_DIR="$VAULT/_inbox/raw/papers"
CLAUDE_BIN="$(command -v claude 2>/dev/null || echo '/usr/local/bin/claude')"

mkdir -p "$VAULT/_logs"
echo "=== Corpus Rebuild $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" | tee -a "$LOG"

# Vérifier prérequis
if ! command -v claude &>/dev/null && [ ! -f "$CLAUDE_BIN" ]; then
  echo "❌ claude CLI introuvable. Installer : npm install -g @anthropic-ai/claude-code" | tee -a "$LOG"
  exit 1
fi

# Compter les papers disponibles
PAPER_COUNT=$(find "$PAPERS_DIR" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
echo "→ $PAPER_COUNT fichiers dans $PAPERS_DIR" | tee -a "$LOG"

if [ "$PAPER_COUNT" -eq 0 ]; then
  echo "⚠️  Aucun paper trouvé — rebuild ignoré" | tee -a "$LOG"
  exit 0
fi

# Lancer claude pour rebuild via claude-mem MCP
claude --print "Tu dois reconstruire le corpus claude-mem nommé 'research-papers'.
Le corpus couvre tous les fichiers markdown dans : $PAPERS_DIR

Étapes :
1. Appeler mcp__plugin_claude-mem_mcp-search__list_corpora pour vérifier si 'research-papers' existe
2. Si existant → appeler mcp__plugin_claude-mem_mcp-search__rebuild_corpus avec name='research-papers'
3. Si absent → appeler mcp__plugin_claude-mem_mcp-search__build_corpus avec name='research-papers' et path='$PAPERS_DIR'
4. Répondre uniquement : 'Corpus research-papers reconstruit — N fichiers indexés' ou 'Erreur : [message]'
" \
  --allowedTools "mcp__plugin_claude-mem_mcp-search__build_corpus,mcp__plugin_claude-mem_mcp-search__rebuild_corpus,mcp__plugin_claude-mem_mcp-search__list_corpora" \
  2>&1 | tee -a "$LOG"

echo "✓ corpus-rebuild.sh terminé $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$LOG"
