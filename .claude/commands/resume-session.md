---
description: Reconstitue le contexte "où on en est" en ~400 tokens (remplace le rituel manuel de 3-4 reads début de session)
allowed-tools: Bash(git log:*), Bash(git status:*), Bash(git branch:*), Bash(jq:*), Bash(ls:*), Bash(wc:*), Bash(head:*), Bash(tail:*), Bash(stat:*)
---

# /resume-session — Contexte rapide

**Objectif token-efficient** : ~400 tokens pour remplacer un rituel manuel de 2000+ tokens de reads.

## Règles absolues

1. **NE PAS lire de fichiers Markdown** volumineux (`.nightly-prompt.md`, specs, plans) — utilise `wc -l` ou `head -10` uniquement
2. **PAS de prose** — tableaux markdown minimalistes
3. **Sortie cible** : 15-25 lignes max, groupées logiquement

## Exécuter ces commandes dans cet ordre précis

```bash
cd /Users/djemildavid/Documents/Obsidian/KnowledgeBase

# 1. Git context (branche + 5 derniers commits + status count)
echo "=== GIT ==="
git branch --show-current
git log --oneline -5
git status --short 2>/dev/null | wc -l | xargs echo "files modified:"

# 2. Nightly status (extrait champs précis uniquement, pas dump complet)
echo "=== NIGHTLY ==="
jq '{status, last_run, notes_added, enrichment_status, errors}' _logs/last-nightly.json 2>/dev/null || echo "no nightly log"

# 3. NotebookLM status
echo "=== NLM ==="
jq '.' _logs/nlm-status.json 2>/dev/null || echo "no NLM status"

# 4. Tech-debt critiques/hautes ouvertes (grep ciblé dans registry)
echo "=== TECH-DEBT OUVERTES (critique/haute) ==="
grep -E "^### TD-2026-[0-9]+.*(CRITIQUE|HAUTE)" projects/second-brain/tech-debt-registry.md 2>/dev/null | grep -v "✅\|❌" | head -5

# 5. Notes créées/modifiées dans les 2 derniers jours (titre uniquement, pas contenu)
# NOTE : find|sed|head (pas xargs — évite signal 13 sur SIGPIPE)
echo "=== NOTES R\u00c9CENTES (48h) ==="
find projects/second-brain -name "*.md" -mtime -2 -type f 2>/dev/null | sed 's|.*/||' | head -5
```

## Synthèse attendue (format strict)

```markdown
## 🌐 Session context — <branche>

**Git** : 3 commits ahead, N files modified
**Last nightly** : <status> @ <last_run> — N notes added
**NLM** : <status>
**Tech-debt critique** : N ouvertes
**Notes récentes** : <liste 3 fichiers max>

**Prochaine action probable** : <déduction depuis tech-debt + derniers commits>
```

**Ne JAMAIS** :
- Lire `.nightly-prompt.md` (500+ lignes)
- Lire `_meta/LOG.md` complet (utiliser `tail -5` si nécessaire)
- Réexpliquer l'architecture (déjà en memory cross-session)
- Recommander des actions non-alignées avec tech-debt-registry

**Si l'utilisateur veut plus de détails** : lui proposer `/nightly-triage` (pour le nightly) ou `/sprint-task-tracker <plan>` (pour les sprints).
