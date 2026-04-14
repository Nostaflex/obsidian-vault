#!/bin/bash
# Test harness pour le guard de lock de nightly-agent.sh
# Teste 4 scénarios : no-lock, PID vivant, PID mort, lock vieux sans PID

set -u
TESTDIR=$(mktemp -d /tmp/lock-test.XXXXXX)
export HOME="$TESTDIR"
mkdir -p "$TESTDIR/Documents/Obsidian/KnowledgeBase/_logs"
LOCKDIR="$TESTDIR/Documents/Obsidian/KnowledgeBase/_logs/nightly.run"
LOCK_LOG="$TESTDIR/Documents/Obsidian/KnowledgeBase/_logs/nightly-agent.log"
LOCK_MAX_AGE_SECONDS=$((24 * 3600))

# Extraire le guard de la fonction testée
run_guard() {
  bash -c '
    LOCKDIR="'"$LOCKDIR"'"
    LOCK_LOG="'"$LOCK_LOG"'"
    LOCK_MAX_AGE_SECONDS='"$LOCK_MAX_AGE_SECONDS"'
    if ! mkdir "$LOCKDIR" 2>/dev/null; then
      STALE=0
      STALE_REASON=""
      LOCK_PID=$(cat "$LOCKDIR/pid" 2>/dev/null || echo "")
      if [ -n "$LOCK_PID" ] && ! kill -0 "$LOCK_PID" 2>/dev/null; then
        STALE=1
        STALE_REASON="pid $LOCK_PID dead"
      else
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
        echo "RECLAIM: $STALE_REASON"
        rm -rf "$LOCKDIR"
        mkdir "$LOCKDIR" || { echo "FAIL: cannot reclaim"; exit 1; }
        echo "$$" > "$LOCKDIR/pid"
        exit 0
      else
        echo "SKIP: pid=$LOCK_PID"
        exit 2
      fi
    fi
    echo "$$" > "$LOCKDIR/pid"
    echo "ACQUIRE: pid=$$"
  '
}

# ── Scénario 1 — pas de lock ───────────────────────────────
echo "=== T1: no lock ==="
rm -rf "$LOCKDIR"
run_guard; RC=$?
[ "$RC" -eq 0 ] && echo "PASS T1" || echo "FAIL T1 (rc=$RC)"

# ── Scénario 2 — lock avec PID vivant (PID de ce shell) ───
echo "=== T2: lock with live PID ==="
rm -rf "$LOCKDIR"
mkdir "$LOCKDIR"
echo "$$" > "$LOCKDIR/pid"  # PID de ce test — vivant
run_guard; RC=$?
[ "$RC" -eq 2 ] && echo "PASS T2 (correctly skipped)" || echo "FAIL T2 (rc=$RC)"

# ── Scénario 3 — lock avec PID mort ────────────────────────
echo "=== T3: lock with dead PID ==="
rm -rf "$LOCKDIR"
mkdir "$LOCKDIR"
echo "99999" > "$LOCKDIR/pid"  # PID improbable (>max sur macOS)
run_guard; RC=$?
[ "$RC" -eq 0 ] && echo "PASS T3 (correctly reclaimed)" || echo "FAIL T3 (rc=$RC)"

# ── Scénario 4 — lock vieux sans PID ──────────────────────
echo "=== T4: old lock no PID ==="
rm -rf "$LOCKDIR"
mkdir "$LOCKDIR"
# Forcer mtime à 2 jours dans le passé
touch -t "$(date -v-2d +%Y%m%d%H%M.%S 2>/dev/null || date -d '2 days ago' +%Y%m%d%H%M.%S)" "$LOCKDIR"
run_guard; RC=$?
[ "$RC" -eq 0 ] && echo "PASS T4 (correctly reclaimed by age)" || echo "FAIL T4 (rc=$RC)"

# ── Scénario 5 — lock récent sans PID (edge case) ─────────
echo "=== T5: recent lock no PID ==="
rm -rf "$LOCKDIR"
mkdir "$LOCKDIR"
# Pas de fichier pid, mtime récent → doit skip (pas reclaim)
run_guard; RC=$?
[ "$RC" -eq 2 ] && echo "PASS T5 (correctly skipped)" || echo "FAIL T5 (rc=$RC)"

# Cleanup
rm -rf "$TESTDIR"
echo "=== done ==="
