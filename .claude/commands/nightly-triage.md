---
description: Diagnostic post-nightly en ~500 tokens — remplace le grep manuel dans 5 fichiers _logs/ chaque matin
allowed-tools: Bash(jq:*), Bash(wc:*), Bash(head:*), Bash(tail:*), Bash(grep:*), Bash(find:*), Bash(ls:*), Bash(stat:*)
---

# /nightly-triage — Diagnostic matinal du run nocturne

**Objectif token-efficient** : ~500 tokens pour un rapport actionnable de l'état du nightly.

## Règles absolues

1. **JAMAIS** dumper `maintenance-report.md` en entier (134 lignes). Extraire uniquement sections via `grep -A N`.
2. **JAMAIS** dumper `nightly-agent.log` (rotation 1-5, potentiellement Mo). Utiliser `tail -20` max.
3. **Toujours** extraire champs JSON précis avec `jq`, pas dumper.

## Exécuter ces commandes dans cet ordre

```bash
cd /Users/djemildavid/Documents/Obsidian/KnowledgeBase

# 1. Nightly principal — 6 champs clés uniquement
echo "=== NIGHTLY SUMMARY ==="
jq '{status, last_run, notes_added, enrichment_status, errors: (.errors | length), health}' _logs/last-nightly.json 2>/dev/null

# 2. NotebookLM status (Track B)
echo "=== NLM STATUS ==="
jq '{status, consecutive_failures, complete, timestamp}' _logs/nlm-status.json 2>/dev/null || echo "no NLM status"

# 3. Alertes actives (detection ALERT dans maintenance-report)
echo "=== ALERTES ACTIVES ==="
grep -E "^(#{1,3})\s*(ALERT|🚨|⚠️)" _logs/maintenance-report.md 2>/dev/null | head -10

# 4. Broken wikilinks — count + exemples
echo "=== BROKEN WIKILINKS ==="
BROKEN_COUNT=$(wc -l <_logs/broken-links.txt 2>/dev/null | tr -d ' ')
echo "Count: $BROKEN_COUNT"
[ "$BROKEN_COUNT" -gt "0" ] && head -5 _logs/broken-links.txt

# 5. iCloud conflicts
echo "=== ICLOUD CONFLICTS ==="
CONFLICTS_COUNT=$(wc -l <_logs/conflicts.txt 2>/dev/null | tr -d ' ')
echo "Count: $CONFLICTS_COUNT"
[ "$CONFLICTS_COUNT" -gt "0" ] && head -3 _logs/conflicts.txt

# 6. Erreurs récentes du nightly-agent.log (20 dernières lignes)
echo "=== LOG TAIL (last 20 lignes) ==="
tail -20 _logs/nightly-agent.log 2>/dev/null | grep -E "(ERROR|WARN|🚨|⚠️|FAIL)" | head -5 || echo "(aucune erreur recent)"

# 7. Derniers concepts ajoutés (titres uniquement, pas contenu)
echo "=== NOUVEAUX CONCEPTS (24h) ==="
find _inbox/raw/concepts -name "*.md" -mtime -1 -type f 2>/dev/null | wc -l | xargs echo "nouveaux concepts:"
```

## Format de sortie attendu

```markdown
## 🌙 Nightly triage — YYYY-MM-DD

| Check | Status | Détail |
|-------|--------|--------|
| Run nightly | ✅/⚠️/❌ | `<status>` @ `<last_run>` |
| NotebookLM | ✅/⚠️/❌ | `<status>`, `<failures>` fails |
| Enrichment | ✅/⚠️ | `<enrichment_status>` |
| Wikilinks cassés | N | (3 premiers si > 0) |
| Conflits iCloud | N | (1er si > 0) |
| Concepts ajoutés | N | (dernières 24h) |

## 🎯 Actions priorisées

1. **[Priorité]** Action concrète avec référence fichier
2. ...

## 📋 Alertes actives

- Liste max 3 alertes les plus graves
```

## Priorisation des actions

Ordre de gravité (du plus urgent au moins urgent) :
1. 🔴 Status `failed` ou `in_progress` (crash non restauré)
2. 🔴 Conflits iCloud (blocage complet vault)
3. 🟠 NLM `degraded` avec failures > 2
4. 🟠 Enrichment `error`
5. 🟡 Broken wikilinks > 10
6. 🟡 Zéro concept ajouté (pipeline inactif)

**Ne JAMAIS** :
- Proposer de re-run le nightly sans diagnostic préalable
- Modifier des fichiers `_logs/` (sauf demande explicite)
- Dumper le contenu complet d'un log
