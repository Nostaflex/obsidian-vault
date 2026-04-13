#!/bin/bash
# nightly-agent.sh — Agent nocturne Second Brain (Light Mode)
# Lancé par launchd à 2h17 chaque nuit via com.second-brain.nightly.plist
#
# Prérequis :
#   - claude CLI installé : npm install -g @anthropic-ai/claude-code
#   - jq installé : brew install jq
#   - Vault initialisé : ~/Documents/Obsidian/KnowledgeBase/
#
# Pour tester manuellement :
#   bash ~/Documents/Obsidian/KnowledgeBase/nightly-agent.sh
set -euo pipefail

# ── Concurrent guard (mkdir lock) ────────────────────────────────────────────
# Empêche deux instances simultanées (ex: launchd retry pendant un run long).
# mkdir est atomique sur tout système POSIX — pas de dépendance externe.
LOCKDIR="${HOME}/Documents/Obsidian/KnowledgeBase/_logs/nightly.run"
if ! mkdir "$LOCKDIR" 2>/dev/null; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Nightly already running (lock held) — skip" \
    >> "${HOME}/Documents/Obsidian/KnowledgeBase/_logs/nightly-agent.log"
  exit 0
fi
trap "rmdir '$LOCKDIR' 2>/dev/null || true" EXIT

VAULT="$HOME/Documents/Obsidian/KnowledgeBase"
PROMPT="$VAULT/.nightly-prompt.md"
LOG="$VAULT/_logs/nightly-agent.log"
CLAUDE_BIN="$(command -v claude 2>/dev/null || echo '/usr/local/bin/claude')"

# Guard run-once-a-day
LAST_NIGHTLY_RUN=$( (jq -r '.last_run // ""' "$VAULT/_logs/last-nightly.json" 2>/dev/null || echo "") | cut -c1-10)
TODAY=$(date -u +%Y-%m-%d)
if [ "$LAST_NIGHTLY_RUN" = "$TODAY" ]; then
  echo "→ Nightly déjà exécuté aujourd'hui ($TODAY) — skip"
  exit 0
fi

# Rotation log (garder les 5 derniers runs)
if [ -f "$LOG" ]; then
  for i in 4 3 2 1; do
    [ -f "${LOG}.${i}" ] && mv "${LOG}.${i}" "${LOG}.$((i+1))"
  done
  mv "$LOG" "${LOG}.1"
fi

echo "=== Nightly Agent $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" > "$LOG"

# 0. Vérifier prérequis
if [ ! -f "$CLAUDE_BIN" ] && ! command -v claude &>/dev/null; then
  echo "❌ claude CLI introuvable. Installer : npm install -g @anthropic-ai/claude-code" >> "$LOG"
  exit 1
fi

if [ ! -f "$PROMPT" ]; then
  echo "❌ Prompt introuvable : $PROMPT" >> "$LOG"
  exit 1
fi

# 1. Pré-run : integrity-check (Python — migré depuis bash 2026-04-13, TD-2026-016)
echo "→ integrity-check..." >> "$LOG"
python3 "$VAULT/integrity_check.py" >> "$LOG" 2>&1
INTEGRITY_RC=$?
if [ "$INTEGRITY_RC" -eq 2 ]; then
  # Exit 2 = conflits iCloud détectés — action manuelle requise, on stoppe
  echo "🚨 integrity-check : conflits iCloud détectés — run nocturne annulé (fix les conflits d'abord)" >> "$LOG"
  exit 2
elif [ "$INTEGRITY_RC" -ne 0 ]; then
  # Fix TD-2026-017 : plus de masquage silencieux des échecs critiques (rsync, restore)
  echo "🚨 integrity-check a échoué (exit $INTEGRITY_RC) — run nocturne annulé pour éviter corruption" >> "$LOG"
  exit 1
fi

# 2. Lancer l'agent nocturne
echo "→ Lancement agent nocturne..." >> "$LOG"
claude --print "$(cat "$PROMPT")" \
  --allowedTools "Bash,Read,Write,Edit,Glob,Grep" \
  >> "$LOG" 2>&1

echo "=== Terminé $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" >> "$LOG"
