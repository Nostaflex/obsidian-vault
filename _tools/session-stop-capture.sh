#!/bin/bash
# session-stop-capture.sh — Stop hook pour Session Capture Pipeline
# Déclenché par Claude Code après chaque réponse complète (Stop event).
# Responsabilité unique : pre-filter + délégation à session_extractor.py.
#
# Payload stdin (Claude Code) : {"session_id": "...", "transcript_path": "..."}
# Timeout configuré : 15s dans settings.json

set -euo pipefail

VAULT="$HOME/Documents/Obsidian/KnowledgeBase"
CHECKPOINT="$VAULT/_logs/session-checkpoint.json"
LOG="$VAULT/_logs/session-extractor.log"
WIP_DIR="$VAULT/_inbox/session"
PYTHON="$(command -v python3 2>/dev/null || echo '/usr/bin/python3')"

# Safety : vault doit exister
[ -d "$VAULT" ] || exit 0
[ -d "$WIP_DIR" ] || exit 0

# ── 1. Parser le payload stdin ───────────────────────────────────────────────

payload=$(cat 2>/dev/null || echo '{}')

session_id=$(echo "$payload" | "$PYTHON" -c \
  "import json,sys; d=json.load(sys.stdin); print(d.get('session_id',''))" 2>/dev/null || echo '')

transcript_path=$(echo "$payload" | "$PYTHON" -c \
  "import json,sys; d=json.load(sys.stdin); print(d.get('transcript_path',''))" 2>/dev/null || echo '')

# ── 2. Fallback découverte transcript si absent ──────────────────────────────

if [ -z "$transcript_path" ] || [ ! -f "$transcript_path" ]; then
  project_encoded=$(echo "$VAULT" | sed 's|/Users/||' | sed 's|/|-|g')
  transcript_path=$(ls -t "$HOME/.claude/projects/-Users-${project_encoded}"/*.jsonl 2>/dev/null | head -1 || echo '')
fi

if [ -z "$transcript_path" ] || [ ! -f "$transcript_path" ]; then
  transcript_path=$(find "$HOME/.claude/projects/" -name "*.jsonl" -newer "$VAULT/_logs/nightly-agent.log" -type f 2>/dev/null | \
    xargs ls -t 2>/dev/null | head -1 || echo '')
fi

[ -f "$transcript_path" ] || exit 0

# ── 3. Pre-filter shell : delta suffisant ? ──────────────────────────────────

last_offset=0
if [ -f "$CHECKPOINT" ]; then
  last_offset=$("$PYTHON" -c \
    "import json; print(json.load(open('$CHECKPOINT')).get('last_offset',0))" 2>/dev/null || echo 0)
fi

current_lines=$(wc -l < "$transcript_path" 2>/dev/null | tr -d ' ' || echo 0)
delta=$((current_lines - last_offset))

# Skip si delta < 3 lignes (pas d'échange complet)
[ "$delta" -lt 3 ] && exit 0

# ── 4. Déléguer à Python ─────────────────────────────────────────────────────

"$PYTHON" "$VAULT/_tools/session_extractor.py" \
  --transcript "$transcript_path" \
  --session-id "${session_id:-unknown}" \
  --checkpoint "$CHECKPOINT" \
  --wip-dir "$WIP_DIR" \
  --log "$LOG" 2>/dev/null || true

exit 0
