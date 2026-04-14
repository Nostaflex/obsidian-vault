#!/bin/bash
# session-end-checkpoint.sh
# ────────────────────────────────────────────────────────────────────────────
# Called by Claude Code SessionEnd hook (project-scope .claude/settings.json).
# Writes a fresh session_pointer.md into the auto-memory directory so the next
# session boot has accurate git state without needing to re-read conversation.
#
# Design constraints :
# - Fast (< 5s) — session is closing, don't block.
# - Deterministic — pure git state capture, no LLM calls.
# - Atomic — write-temp + rename so MEMORY.md never sees half-written content.
# - Idempotent — running twice produces same output.
#
# For richer summaries, user can invoke /resume-session skill or manually edit
# session_pointer.md before the next session.
#
# Reads stdin (Claude Code provides SessionEnd payload) — ignores it.
# Exits 0 on success or silent no-op (never blocks session close).

set -eo pipefail

VAULT="$HOME/Documents/Obsidian/KnowledgeBase"
MEMORY_DIR="$HOME/.claude/projects/-Users-djemildavid-Documents-Obsidian-KnowledgeBase/memory"
POINTER="$MEMORY_DIR/session_pointer.md"

# Safety : if paths don't exist, silent no-op (don't break session close)
[ -d "$VAULT" ] || exit 0
[ -d "$MEMORY_DIR" ] || exit 0

cd "$VAULT" 2>/dev/null || exit 0

# Capture state (all commands have `|| echo ""` fallback so nothing blocks)
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
LAST_COMMIT=$(git log -1 --format='%h %s' 2>/dev/null || echo "no-commits")
COMMITS_24H=$(git log --since='24 hours ago' --oneline 2>/dev/null | head -15 || echo "")
WORKING_TREE=$(git status --short 2>/dev/null | grep -v '^?? _logs' | grep -v '^?? \.coverage' | grep -v '^?? integrity-check.sh' | head -8 || echo "")
OPEN_PRS=$(gh pr list --state open --json number,title 2>/dev/null | python3 -c "import json,sys; data=json.load(sys.stdin); print('\n'.join(f\"  - #{p['number']}: {p['title']}\" for p in data)) if data else print('  (none)')" 2>/dev/null || echo "  (gh not available)")

# Build pointer content
TMP=$(mktemp "${POINTER}.XXXX")
cat > "$TMP" <<POINTER_EOF
---
name: session_pointer
description: Auto-generated session pointer. Updated by SessionEnd hook (_tools/session-end-checkpoint.sh). Reflects git state at last session close.
type: project
---

# Session Pointer

**Last session end** : $TS

## Git state

- **Branch** : $BRANCH
- **Last commit** : $LAST_COMMIT

## Recent commits (24h)

\`\`\`
$COMMITS_24H
\`\`\`

## Working tree (hors artifacts nightly)

\`\`\`
$WORKING_TREE
\`\`\`

## Open PRs

$OPEN_PRS

## Retrieval strategy (prochaine session)

- Contexte projet général : \`/load-moc <topic>\`
- Contexte conversationnel historique : \`mcp__claude-mem__search\`
- Pour reconstitution "où on en est" : skill \`/resume-session\`

<!-- This file is auto-regenerated. Manual edits will be overwritten. -->
POINTER_EOF

# Atomic replace (POSIX guarantees atomicity of rename on same filesystem)
mv "$TMP" "$POINTER"

exit 0
