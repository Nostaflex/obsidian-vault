#!/bin/bash
# integrity-check.sh — exécuté avant chaque run nocturne agent
# Coût : 0 token — Bash pur
# Déployer dans : ~/Documents/Obsidian/KnowledgeBase/integrity-check.sh
set -euo pipefail

VAULT="$HOME/Documents/Obsidian/KnowledgeBase"
BACKUP="$HOME/.second-brain-backup" # hors iCloud — caché, jamais synchronisé
LOGS="$VAULT/_logs"
META="$VAULT/_meta"

echo "=== integrity-check $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

# 0. Forcer le téléchargement des fichiers iCloud (placeholders .icloud → fichiers réels)
#    Nécessaire si "Optimiser le stockage Mac" est activé dans iCloud
if command -v brctl &>/dev/null; then
  echo "↓ Téléchargement iCloud en cours..."
  brctl download "$VAULT" 2>/dev/null || true
  echo "✓ Fichiers iCloud disponibles localement"
fi

# 1. Backup atomique (hors iCloud — ~/.second-brain-backup/)
mkdir -p "$BACKUP"
rsync -a --quiet "$VAULT/" "$BACKUP/" \
  --exclude="*.icloud" \
  --exclude="* conflicted copy*"
echo "✓ Backup OK → $BACKUP"

# 2. Détecter crash run précédent
if [ -f "$LOGS/last-nightly.json" ]; then
  STATUS=$(jq -r '.status // "unknown"' "$LOGS/last-nightly.json" 2>/dev/null || echo "unknown")
  if [ "$STATUS" = "in_progress" ]; then
    echo "⚠️  Run précédent interrompu (status: in_progress) — restore depuis backup"
    rsync -a --quiet "$BACKUP/" "$VAULT/" \
      --exclude="sensitive.nosync"
    jq '.status = "restored_after_crash"' "$LOGS/last-nightly.json" >/tmp/nightly.tmp &&
      mv /tmp/nightly.tmp "$LOGS/last-nightly.json"
    echo "✓ Vault restauré depuis $BACKUP"
  fi
fi

# 3. Détecter copies de conflit iCloud
CONFLICTS=$(find "$VAULT" -name "* conflicted copy*" 2>/dev/null | wc -l | tr -d ' ')
if [ "$CONFLICTS" -gt "0" ]; then
  find "$VAULT" -name "* conflicted copy*" 2>/dev/null >"$LOGS/conflicts.txt"
  echo "⚠️  $CONFLICTS copie(s) de conflit iCloud détectée(s) → $LOGS/conflicts.txt"
  echo "    Résoudre manuellement dans Obsidian avant de continuer"
else
  >"$LOGS/conflicts.txt"
  echo "✓ Aucune copie de conflit iCloud"
fi

# 4. Reconstruire INDEX.md depuis fichiers réels (exclut sensitive.nosync et .icloud)
NOTE_COUNT=$(
  find "$VAULT/universal" "$VAULT/projects" -name "*.md" \
    ! -name "INDEX.md" ! -name "VAULT.md" ! -name "context-*.md" \
    ! -name "*.icloud" 2>/dev/null |
    wc -l | tr -d ' '
)

{
  echo "# INDEX — Knowledge Base"
  echo ""
  echo "Mis à jour : $(date +%Y-%m-%d) | Notes actives : $NOTE_COUNT | Plafond : 300"
  echo ""
  echo "_Dérivé — recalculé par integrity-check.sh avant chaque run nocturne._"
  echo "_Ne pas éditer manuellement._"
  echo ""
  echo "---"
  echo ""
  find "$VAULT/universal" "$VAULT/projects" -name "*.md" \
    ! -name "INDEX.md" ! -name "VAULT.md" ! -name "context-*.md" \
    ! -name "*.icloud" \
    2>/dev/null | sort | while read -r f; do
    TITLE=$(head -1 "$f" 2>/dev/null | sed 's/^# //')
    TAGS=$(grep "^Tags:" "$f" 2>/dev/null | sed 's/^Tags: //' || echo "—")
    RELPATH="${f#$VAULT/}"
    echo "- [$TITLE]($RELPATH) — $TAGS"
  done
} >/tmp/INDEX_rebuilt.md

echo "✓ INDEX.md reconstruit ($NOTE_COUNT notes) → /tmp/INDEX_rebuilt.md"

# 5. Vérifier wikilinks cassés — macOS BSD grep compatible (sed extraction)
>/tmp/broken-links.txt
# Extraire [[liens]] via sed (grep -o \[\[ non fiable sur BSD grep macOS)
LINKS=$(grep -r '\[\[' "$VAULT/universal" "$VAULT/projects" 2>/dev/null \
  | grep -v '\.icloud:' \
  | sed -n 's/.*\[\[\([^]]*\)\]\].*/\1/p' \
  | sort -u || true)

if [ -n "$LINKS" ]; then
  while IFS= read -r LINK; do
    # Obsidian wikilinks = filename (sans extension), pas le titre H1
    FOUND=$(find "$VAULT/universal" "$VAULT/projects" \
      -name "${LINK}.md" ! -name "*.icloud" 2>/dev/null | head -1 || true)
    if [ -z "$FOUND" ]; then
      echo "BROKEN: [[$LINK]]" >>/tmp/broken-links.txt
    fi
  done <<<"$LINKS"
fi

cp /tmp/broken-links.txt "$LOGS/broken-links.txt"
BROKEN=$(wc -l <"$LOGS/broken-links.txt" | tr -d ' ')
if [ "$BROKEN" -gt "0" ]; then
  echo "⚠️  $BROKEN wikilink(s) cassé(s) → $LOGS/broken-links.txt"
  cat "$LOGS/broken-links.txt"
else
  echo "✓ Aucun wikilink cassé"
fi

echo "=== integrity-check terminé ==="
