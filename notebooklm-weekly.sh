#!/bin/bash
# notebooklm-weekly.sh — Track B wrapper
# Runs weekly, deadline Sunday 23:30.
# Usage: bash notebooklm-weekly.sh [--domain DOMAIN] [--dry-run]
#
# Prerequisite: NLM_MCP_CMD set, auth.json configured
set -euo pipefail

VAULT="$HOME/Documents/Obsidian/KnowledgeBase"
LOG="$VAULT/_logs/nlm-weekly.log"
PYTHON="$(command -v python3)"

# Timeout guard: abort if past 23:30
HOUR=$(date +%H); MIN=$(date +%M)
if [ "$HOUR" -gt 23 ] || { [ "$HOUR" -eq 23 ] && [ "$MIN" -gt 30 ]; }; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Past 23:30 deadline — aborting" >> "$LOG"
  # Write incomplete sentinel so nightly agent skips B-track
  python3 -c "
import json, pathlib
p = pathlib.Path('$VAULT/_logs/nlm-status.json')
data = json.loads(p.read_text()) if p.exists() else {}
data.update({'complete': False, 'reason': 'deadline_exceeded'})
p.write_text(json.dumps(data, indent=2))
"
  exit 0
fi

echo "=== NLM Weekly $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" >> "$LOG"
caffeinate -i "$PYTHON" "$VAULT/notebooklm_weekly.py" "$@" >> "$LOG" 2>&1
echo "=== Done $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" >> "$LOG"
