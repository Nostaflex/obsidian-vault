#!/bin/bash
# session-transcript-finalizer.sh — SessionEnd hook finalizer
# Responsabilité unique : WIP → note finalisée + cleanup checkpoint.
# Déclenché par Claude Code au SessionEnd, APRÈS session-end-checkpoint.sh.
#
# Payload stdin : {"session_id": "...", "transcript_path": "..."}
# session_id utilisé pour valider la cohérence avec le checkpoint.

set -euo pipefail

VAULT="$HOME/Documents/Obsidian/KnowledgeBase"
CHECKPOINT="$VAULT/_logs/session-checkpoint.json"
LOG="$VAULT/_logs/session-extractor.log"
WIP_DIR="$VAULT/_inbox/session"
PYTHON="$(command -v python3 2>/dev/null || echo '/usr/bin/python3')"

# Safety
[ -d "$VAULT" ] || exit 0

# ── 1. Lire payload stdin ────────────────────────────────────────────────────

payload=$(cat 2>/dev/null || echo '{}')
payload_session_id=$("$PYTHON" -c \
  "import json,sys; d=json.loads('$payload' if '$payload' != '' else '{}'); print(d.get('session_id',''))" 2>/dev/null || echo '')

# ── 2. Lire le WIP path depuis checkpoint ────────────────────────────────────

[ -f "$CHECKPOINT" ] || exit 0

ck_session_id=$("$PYTHON" -c \
  "import json; print(json.load(open('$CHECKPOINT')).get('session_id',''))" 2>/dev/null || echo '')
wip_path=$("$PYTHON" -c \
  "import json; print(json.load(open('$CHECKPOINT')).get('wip_path',''))" 2>/dev/null || echo '')

# Si payload session_id présent et incohérent avec checkpoint → skip (session différente)
if [ -n "$payload_session_id" ] && [ -n "$ck_session_id" ] && [ "$payload_session_id" != "$ck_session_id" ]; then
  exit 0
fi

# Pas de WIP = session sans décisions capturées → exit propre
if [ -z "$wip_path" ] || [ ! -f "$wip_path" ]; then
  rm -f "$CHECKPOINT"
  exit 0
fi

# ── 2. Mettre à jour le frontmatter status ───────────────────────────────────

sed -i '' 's/status: in-progress/status: complete/' "$wip_path" 2>/dev/null || true

# ── 3. Rename atomique WIP → note finalisée ──────────────────────────────────

date_str=$(date +%Y-%m-%d)
session_short=$(basename "$wip_path" | sed 's/wip-//' | sed 's/\.md//')
final_name="session-${date_str}-${session_short}.md"
final_path="$WIP_DIR/$final_name"

mv "$wip_path" "$final_path"

# ── 4. Cleanup checkpoint ────────────────────────────────────────────────────

rm -f "$CHECKPOINT"

# ── 5. Log ───────────────────────────────────────────────────────────────────

ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "$ts | FINALIZE | wip-${session_short}.md → $final_name" >> "$LOG" 2>/dev/null || true

exit 0
