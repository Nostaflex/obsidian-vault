# Memory Migration — Validation Metrics (2026-04-13)

## Baseline (avant migration)

- Boot cost: ~28 000 tokens (14% de 200K)
- Memory files: 8 fichiers, 18 474 bytes (~5 280 tokens chargés via claudeMd)
- Timeline priming claude-mem: ~11 800 tokens (50 observations injectées au boot)

## Post-migration (mesuré 2026-04-13 après restart)

### Mesurable côté disque (confirmé)

- Memory files: **3 fichiers, 1 907 bytes (~476 tokens)** — réduction 90%
  - `MEMORY.md` (467 B) — pointer minimal vers user_profile + session_pointer
  - `user_profile.md` (830 B) — role, stack, préférences
  - `session_pointer.md` (610 B) — branche, goal
- claude-mem injection désactivée :
  - `CLAUDE_MEM_CONTEXT_OBSERVATIONS = 0` (était "50")
  - `CLAUDE_MEM_CONTEXT_SHOW_LAST_SUMMARY = false` (était "true")
- claude-mem search préservé :
  - `CLAUDE_MEM_CHROMA_ENABLED = true`
  - MCP server `mcp__plugin_claude-mem_mcp-search__*` accessible

### Mesurable côté session (à compléter par user)

- Boot cost en tokens : TBD
- Boot cost en % : TBD

## Target vs Acceptable

| Métrique | Cible | Acceptable | Mesuré |
|----------|-------|------------|--------|
| Memory files (bytes) | < 2 000 | < 3 000 | **1 907 ✅** |
| Memory files (tokens) | < 500 | < 800 | **~476 ✅** |
| Boot cost (tokens) | 500 | < 2 000 | TBD |
| Boot cost (%) | 0.25% | < 1% | TBD |

## 5 scenarios de validation

À exécuter dans une session Claude Code fraîche (post-restart). Chaque scenario = 1 prompt à Claude + observation comportement.

### Scenario 1: Query simple (pointer direct)
- **Prompt** : "Quelles sont les règles bash vs python du projet ?"
- **Attente** : Claude utilise le pointer `[[decision-bash-vs-python-boundary]]` depuis user_profile.md, lit la note vault directement
- **Tokens consommés** : TBD
- **Statut** : TBD

### Scenario 2: Query topic connu (via MOC)
- **Prompt** : `/load-moc architecture` puis "synthétise les décisions clés"
- **Attente** : Tier 1 route vers `moc-architecture`, charge le MOC, suit wikilinks
- **Tokens** : TBD
- **Statut** : TBD

### Scenario 3: Query topic inconnu (fallback Chroma)
- **Prompt** : `/load-moc 'pattern verbose reduction'`
- **Attente** : Tier 1 miss → Tier 2 `mcp__claude-mem__search`
- **Tokens** : TBD
- **Statut** : TBD

### Scenario 4: Query historique
- **Prompt** : "Qu'est-ce qu'on a fait dans la session d'hier ?"
- **Attente** : Claude invoke `mcp__claude-mem__timeline` ou `search`
- **Tokens** : TBD
- **Statut** : TBD

### Scenario 5: /resume-session
- **Prompt** : `/resume-session`
- **Note** : skill créé sur PR#2 (branche `feat/token-efficient-custom-skills`), pas merged sur main → indisponible sur cette branche
- **Statut** : N/A (sera dispo après merge PR#2)

## Conclusions

À compléter après exécution des scenarios.

## Rollback si besoin

```bash
# Restaurer les 7 memory files legacy
tar xzf /tmp/memory-backup-2026-04-13T152946Z.tar.gz \
  -C "$HOME/.claude/projects/-Users-djemildavid-Documents-Obsidian-KnowledgeBase/memory/"

# Restaurer settings claude-mem
cp /tmp/claude-mem-settings.backup.20260413.json ~/.claude-mem/settings.json

# Redémarrer Claude Code
```
