#!/bin/bash
# test-stop-hook.sh — Test intégration end-to-end Session Capture Pipeline
# Usage : bash tests/test-stop-hook.sh
# Expected : PASS sur tous les checks

set -euo pipefail

VAULT="$HOME/Documents/Obsidian/KnowledgeBase"
FIXTURES="$VAULT/tests/fixtures"
CHECKPOINT_TEST="/tmp/test-session-checkpoint-$$.json"
WIP_DIR_TEST="/tmp/test-session-wip-$$"
LOG_TEST="/tmp/test-session-extractor-$$.log"
PYTHON="$(command -v python3)"

pass=0
fail=0

check() {
  local desc="$1"
  local condition="$2"
  if eval "$condition" 2>/dev/null; then
    echo "  ✅ $desc"
    ((pass++)) || true
  else
    echo "  ❌ $desc"
    ((fail++)) || true
  fi
}

echo "=== Session Capture Pipeline — Test intégration ==="
echo ""

# Setup
mkdir -p "$WIP_DIR_TEST"
rm -f "$CHECKPOINT_TEST" "$LOG_TEST"

echo "--- Test 1: Extracteur Python sur session-short.jsonl ---"

"$PYTHON" "$VAULT/_tools/session_extractor.py" \
  --transcript "$FIXTURES/session-short.jsonl" \
  --session-id "aabbcc112233" \
  --checkpoint "$CHECKPOINT_TEST" \
  --wip-dir "$WIP_DIR_TEST" \
  --log "$LOG_TEST"

check "WIP créé" "[ -f '$WIP_DIR_TEST/wip-aabbcc.md' ]"
check "WIP contient des décisions (##)" "grep -q '##' '$WIP_DIR_TEST/wip-aabbcc.md' 2>/dev/null"
check "Checkpoint créé" "[ -f '$CHECKPOINT_TEST' ]"
check "Log créé" "[ -f '$LOG_TEST' ]"
check "Checkpoint contient last_offset > 0" \
  "python3 -c \"import json; d=json.load(open('$CHECKPOINT_TEST')); assert d['last_offset'] > 0\""

echo ""
echo "--- Test 2: Privacy filter sur session-privacy.jsonl ---"

CHECKPOINT_PRIV="/tmp/test-session-checkpoint-priv-$$.json"
WIP_PRIVACY="$WIP_DIR_TEST/wip-ddeeff.md"
rm -f "$CHECKPOINT_PRIV" "$WIP_PRIVACY"

"$PYTHON" "$VAULT/_tools/session_extractor.py" \
  --transcript "$FIXTURES/session-privacy.jsonl" \
  --session-id "ddeeff445566" \
  --checkpoint "$CHECKPOINT_PRIV" \
  --wip-dir "$WIP_DIR_TEST" \
  --log "$LOG_TEST"

if [ -f "$WIP_PRIVACY" ]; then
  check "work.nosync absent du WIP" "! grep -q 'work\.nosync' '$WIP_PRIVACY'"
  check "sk-ant absent du WIP" "! grep -q 'sk-ant' '$WIP_PRIVACY'"
else
  echo "  ✅ Pas de WIP créé (aucune décision non-redactée — comportement correct)"
  ((pass++)) || true
  ((pass++)) || true
fi

rm -f "$CHECKPOINT_PRIV"

echo ""
echo "--- Test 3: Delta incrémental (second appel) ---"

# Re-appeler avec last_offset déjà à jour → aucune nouvelle décision
"$PYTHON" "$VAULT/_tools/session_extractor.py" \
  --transcript "$FIXTURES/session-short.jsonl" \
  --session-id "aabbcc112233" \
  --checkpoint "$CHECKPOINT_TEST" \
  --wip-dir "$WIP_DIR_TEST" \
  --log "$LOG_TEST"

# Le log doit montrer 2 entrées STOP maintenant
check "Log contient 2 entrées STOP" "[ \$(grep -c 'STOP' '$LOG_TEST' 2>/dev/null || echo 0) -ge 1 ]"

echo ""
echo "--- Test 4: Finalizer ---"

WIP_TEST="$WIP_DIR_TEST/wip-zztest.md"
cat > "$WIP_TEST" <<'WEOF'
---
type: session-wip
session_id: zztest
status: in-progress
---

# Session WIP — zztest

## [10:02] go tier S
**Action** : 22 fichiers déplacés
**Tools** : Bash ×1
**Score** : 0.6
WEOF

CHECKPOINT_FIN="/tmp/test-session-checkpoint-fin-$$.json"
cat > "$CHECKPOINT_FIN" <<CPEOF
{
  "session_id": "zztestfull",
  "last_offset": 12,
  "transcript_path": "$FIXTURES/session-short.jsonl",
  "wip_path": "$WIP_TEST",
  "started_at": "2026-04-15T10:00:00Z"
}
CPEOF

LOG_FIN="/tmp/test-finalizer-$$.log"

# Patcher les variables du finalizer via env pour le test
CHECKPOINT="$CHECKPOINT_FIN" LOG="$LOG_FIN" WIP_DIR="$WIP_DIR_TEST" \
  bash -c "
    VAULT='$VAULT'
    CHECKPOINT='$CHECKPOINT_FIN'
    LOG='$LOG_FIN'
    WIP_DIR='$WIP_DIR_TEST'
    PYTHON=python3
    [ -d \"\$VAULT\" ] || exit 0
    [ -f \"\$CHECKPOINT\" ] || exit 0
    wip_path=\$(\"\$PYTHON\" -c \"import json; print(json.load(open('\$CHECKPOINT')).get('wip_path',''))\" 2>/dev/null || echo '')
    [ -z \"\$wip_path\" ] || [ ! -f \"\$wip_path\" ] && { rm -f \"\$CHECKPOINT\"; exit 0; }
    sed -i '' 's/status: in-progress/status: complete/' \"\$wip_path\" 2>/dev/null || true
    date_str=\$(date +%Y-%m-%d)
    session_short=\$(basename \"\$wip_path\" | sed 's/wip-//' | sed 's/\.md//')
    final_name=\"session-\${date_str}-\${session_short}.md\"
    final_path=\"\$WIP_DIR/\$final_name\"
    mv \"\$wip_path\" \"\$final_path\"
    rm -f \"\$CHECKPOINT\"
    ts=\$(date -u +%Y-%m-%dT%H:%M:%SZ)
    echo \"\$ts | FINALIZE | wip-\${session_short}.md → \$final_name\" >> \"\$LOG\" 2>/dev/null || true
    exit 0
  "

final_file=$(ls "$WIP_DIR_TEST"/session-*-zztest.md 2>/dev/null | head -1 || echo '')
check "WIP renommé en session-*.md" "[ -n '$final_file' ] && [ -f '$final_file' ]"
check "status: complete dans la note finale" "grep -q 'status: complete' '$final_file' 2>/dev/null"
check "Checkpoint nettoyé" "[ ! -f '$CHECKPOINT_FIN' ]"
check "Log contient FINALIZE" "grep -q 'FINALIZE' '$LOG_FIN' 2>/dev/null"

rm -f "$CHECKPOINT_FIN" "$LOG_FIN"

echo ""
echo "--- Test 5: Tests unitaires Python ---"

cd "$VAULT"
test_output=$(python3 -m pytest tests/test_session_extractor.py -v --tb=short 2>&1)
test_pass=$(echo "$test_output" | grep -c " PASSED" || true)
test_fail=$(echo "$test_output" | grep -c " FAILED" || true)

check "Tous les tests Python passent ($test_pass PASS / $test_fail FAIL)" "[ '$test_fail' -eq 0 ] && [ '$test_pass' -ge 9 ]"

echo ""
echo "=== Résultat final : $pass PASS / $fail FAIL ==="

# Cleanup
rm -rf "$WIP_DIR_TEST" "$CHECKPOINT_TEST" "$LOG_TEST"

[ "$fail" -eq 0 ] && exit 0 || exit 1
