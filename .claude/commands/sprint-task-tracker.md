---
description: Corrèle plan Sprint (task-ids BS-*/F*) avec git log pour voir progression — ~400 tokens
allowed-tools: Bash(git log:*), Bash(grep:*), Bash(wc:*), Bash(sed:*), Bash(sort:*), Bash(awk:*), Bash(head:*), Bash(ls:*)
argument-hint: "<plan-file.md> (optionnel — si omis, prend le plus récent dans docs/superpowers/plans/)"
---

# /sprint-task-tracker — Progression Sprint

**Objectif token-efficient** : ~400 tokens pour un tableau [task-id → commits], détection orphans.

## Règles absolues

1. **NE PAS lire le plan complet** — seulement `grep` pour extraire les task-ids
2. **NE PAS lire les commits** — `--oneline` uniquement
3. **Sortie = tableau markdown compact** avec % progression

## Exécuter ces commandes

```bash
cd /Users/djemildavid/Documents/Obsidian/KnowledgeBase

# 1. Détermine le plan à analyser
# Fix B1 PR#2 review : Claude Code injecte l'argument via $ARGUMENTS, pas $1
PLAN="${ARGUMENTS:-$(ls -t docs/superpowers/plans/*.md 2>/dev/null | head -1)}"
echo "=== PLAN: $PLAN ==="

# Fix B2 PR#2 review : if/then au lieu de exit 1 (qui peut tuer la suite)
if [ ! -f "$PLAN" ]; then
  echo "⚠️  Plan introuvable. Lister les plans disponibles :"
  ls -t docs/superpowers/plans/*.md 2>/dev/null | head -5
else
  # 2. Date de création du plan (pour filtrer git log)
  PLAN_DATE=$(git log --format=%ai --diff-filter=A -- "$PLAN" 2>/dev/null | tail -1 | cut -d' ' -f1)
  [ -z "$PLAN_DATE" ] && PLAN_DATE=$(stat -f %Sm -t %Y-%m-%d "$PLAN" 2>/dev/null)
  echo "Plan date: $PLAN_DATE"

  # 3. Extract task-ids mentionnés dans le plan (patterns spécifiques au projet)
  echo "=== TASK-IDS DU PLAN ==="
  grep -oE '\bBS-[0-9]+|\bF[0-9]+|\bTD-2026-[0-9]+|\b2[A-F]\b' "$PLAN" | sort -u | head -30

  # 4. Commits récents avec task-ids (depuis la date du plan)
  # Fix I2 PR#2 review : -E pour ERE étendue + plus de capture littérale de parenthèses
  echo "=== COMMITS AVEC TASK-ID (depuis plan) ==="
  git log --since="$PLAN_DATE" --pretty=format:"%h %s" -E --grep='BS-[0-9]+|F[0-9]+|TD-2026-[0-9]+|\b2[A-F]\b' 2>/dev/null | head -20

  # 5. Commits "orphans" (pas de task-id) depuis la date du plan — potentiels items non trackés
  echo "=== COMMITS ORPHANS (pas de task-id) ==="
  git log --since="$PLAN_DATE" --pretty=format:"%h %s" 2>/dev/null | grep -vE "BS-[0-9]+|F[0-9]+|TD-2026-[0-9]+|\b2[A-F]\b" | head -10
fi
```

## Format de sortie attendu

```markdown
## 🏃 Sprint progress — `<plan-filename>`

**Plan créé** : YYYY-MM-DD
**Dernière activité** : YYYY-MM-DD

| Task-ID | Status | Commits |
|---------|--------|---------|
| BS-1 | ✅ done | `hash1`, `hash2` |
| BS-2 | ✅ done | `hash3` |
| BS-3 | ⏳ pending | — |
| F22 | ✅ done | `hash4` |

**Progress** : N/M tasks done (XX%)

## 🚩 Orphan commits (pas de task-id)

- `hash` : `message` — à ajouter au plan ? ou quality fix acceptable ?

## 🎯 Reste à faire

- BS-3 : <titre de la task depuis le plan>
```

## Logique de matching task → commit

1. Un task-id est **"done"** si au moins 1 commit contient explicitement le task-id dans son message (`--grep`)
2. Un task-id est **"pending"** si aucun commit depuis la date du plan
3. Les commits "orphans" sont ceux qui n'ont aucun task-id dans leur message — **potentiellement des quality fixes oubliés du plan**

## Si argument vide

Prend automatiquement le plan le plus récent dans `docs/superpowers/plans/`.

**Ne JAMAIS** :
- Modifier le plan (cette skill est lecture seule)
- Proposer d'ajouter des task-ids manquants sans valider avec l'utilisateur
- Dumper le contenu complet du plan
