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

# ── Concurrent guard (mkdir lock + PID + age fallback) ──────────────────────
# Empêche deux instances simultanées (ex: launchd retry pendant un run long).
# mkdir est atomique sur tout système POSIX — pas de dépendance externe.
# TD-2026-018 : détection lock orphelin via PID (kill -9 / OOM / crash launchd
# ne déclenche pas trap EXIT → lock jamais nettoyé → nightly skip silencieux).
LOCKDIR="${HOME}/Documents/Obsidian/KnowledgeBase/_logs/nightly.run"
LOCK_LOG="${HOME}/Documents/Obsidian/KnowledgeBase/_logs/nightly-agent.log"
LOCK_MAX_AGE_SECONDS=$((24 * 3600))  # 24h — un vrai run ne dure jamais si longtemps

if ! mkdir "$LOCKDIR" 2>/dev/null; then
  # Lock présent : orphelin ou légitime ?
  STALE=0
  STALE_REASON=""
  LOCK_PID=$(cat "$LOCKDIR/pid" 2>/dev/null || echo "")
  if [ -n "$LOCK_PID" ] && ! kill -0 "$LOCK_PID" 2>/dev/null; then
    STALE=1
    STALE_REASON="pid $LOCK_PID dead"
  else
    # Pas de PID lisible OU PID vivant : vérifier l'âge du lock
    if [ -d "$LOCKDIR" ]; then
      LOCK_MTIME=$(stat -f %m "$LOCKDIR" 2>/dev/null || stat -c %Y "$LOCKDIR" 2>/dev/null || echo 0)
      NOW=$(date +%s)
      AGE=$((NOW - LOCK_MTIME))
      if [ "$AGE" -gt "$LOCK_MAX_AGE_SECONDS" ]; then
        STALE=1
        STALE_REASON="age ${AGE}s > ${LOCK_MAX_AGE_SECONDS}s"
      fi
    fi
  fi

  if [ "$STALE" -eq 1 ]; then
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] ⚠️  Lock orphelin détecté ($STALE_REASON) — réclamation" \
      >> "$LOCK_LOG"
    rm -rf "$LOCKDIR"
    if ! mkdir "$LOCKDIR" 2>/dev/null; then
      echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] ❌ Impossible de réclamer le lock — skip" \
        >> "$LOCK_LOG"
      exit 1
    fi
  else
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Nightly already running (lock held, pid=$LOCK_PID) — skip" \
      >> "$LOCK_LOG"
    exit 0
  fi
fi

# Écrire le PID courant dans le lock pour diagnostic futur
echo "$$" > "$LOCKDIR/pid"
trap "rm -rf '$LOCKDIR' 2>/dev/null || true" EXIT

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

# 1b. Collecte praticienne (weekends automatique + FORCE_PRACTITIONER=1 pour run manuel)
_is_weekend() { local day; day=$(date +%u); [ "$day" -ge 6 ]; }
if [ "${FORCE_PRACTITIONER:-0}" = "1" ] || _is_weekend; then
  echo "→ practitioner-collector..." >> "$LOG"
  python3 "$VAULT/practitioner_collector.py" --since 7 >> "$LOG" 2>&1 || \
    echo "⚠️  practitioner_collector a échoué (exit $?) — run nocturne continue" >> "$LOG"
fi

# 2. Lancer l'agent nocturne
echo "→ Lancement agent nocturne..." >> "$LOG"
claude --print "$(cat "$PROMPT")" \
  --allowedTools "Bash,Read,Write,Edit,Glob,Grep" \
  >> "$LOG" 2>&1

echo "=== Terminé $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" >> "$LOG"
