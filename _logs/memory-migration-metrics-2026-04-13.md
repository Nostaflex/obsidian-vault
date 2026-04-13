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

### Mesurable côté session (mesuré 2026-04-13 21:13 via `/context`)

| Catégorie | Tokens | Note |
|-----------|--------|------|
| **Memory files (`MEMORY.md` AutoMem)** | **165** | ⭐ Couche optimisée, -97% vs baseline |
| Skills total (dont `/load-moc` 31 tok) | 1 700 | Lazy-loadable |
| System prompt | 6 900 | Claude Code base + CMEM block résiduel |
| System tools built-in actifs | 11 600 | Edit, Read, Bash, Grep, Glob, etc. |
| MCP tools (deferred) | 17 300 | Schémas fetched à la demande via ToolSearch |
| System tools (deferred) | 8 700 | Idem |
| Custom agents | 247 | code-reviewer |
| **Total static boot** | **~20 600** | -26% vs baseline 28K |

**Note** : `user_profile.md` (830 B) et `session_pointer.md` (610 B) ne sont **PAS** auto-loaded — ils ne sont chargés que sur demande explicite (Read par Claude). Seul `MEMORY.md` (le pointer) est dans le boot context.

## Target vs Acceptable

| Métrique | Cible | Acceptable | Mesuré | Verdict |
|----------|-------|------------|--------|---------|
| Memory files on disk (bytes) | < 2 000 | < 3 000 | 1 907 | ✅ |
| Memory files on disk (tokens estim.) | < 500 | < 800 | ~476 | ✅ |
| **Memory files boot cost (tokens)** | **500** | **< 2 000** | **165** | **🎯 dépassé** |
| Boot cost total (tokens) | (n/a) | < 25K | ~20.6K | ✅ |

**Lecture** : la migration a atteint et dépassé sa cible sur la couche cible (memory files = 165 tok vs cible 500). Le boot total reste dominé par les tool schemas (système + MCP) — c'est hors-scope de cette migration et représente un autre chantier potentiel ("tool routing dynamique").

## 5 scenarios de validation

À exécuter dans une session Claude Code fraîche (post-restart). Chaque scenario = 1 prompt à Claude + observation comportement.

### Scenario 1: Query simple (pointer direct)
- **Prompt** : "Quelles sont les règles bash vs python du projet ?"
- **Attente** : Claude utilise le pointer `[[decision-bash-vs-python-boundary]]` depuis user_profile.md, lit la note vault directement
- **Tokens consommés** : TBD
- **Statut** : TBD

### Scenario 2: Query topic connu (via MOC) — **EXÉCUTÉ 2026-04-13 21:18**
- **Prompt** : "Pourquoi a-t-on choisi Anthropic Batch API + Claude Haiku pour `paper_synthesizer.py` ?"
- **Attente** : Tier 1 route vers `moc-architecture`, charge le MOC, suit wikilinks vers `architecture-paper-synthesizer`
- **Tokens** :
  - Tier 1 step 1 (moc-index) : ~470 tok
  - Tier 1 step 2 (moc-architecture) : ~382 tok
  - Lecture directe note (`architecture-paper-synthesizer`) : ~330 tok
  - **Total : ~1 182 tok** (vs cible spec 340 — 3.5× over)
- **Statut** : ✅ Routing correct, ⚠️ budget dépassé, ⚠️ note absente du MOC

**Findings :**
1. ✅ Routing Tier 1 → `moc-architecture` exact match sur "pourquoi ce choix"
2. ✅ Réponse complète : 3 raisons (Gemini EU-bloqué, cost optim, throughput) + source citée
3. ⚠️ **Gap MOC ↔ vault** : `architecture-paper-synthesizer.md` créée aujourd'hui mais absente du MOC car le nightly n'a pas tourné. Le Tier 1 routing aurait raté la note sans lecture directe. → besoin d'un mécanisme "regen MOC on-demand" sur création de note OU déclencher nightly partiel. **Reste en attente (v3 future)**.
4. ⚠️ Budget tokens 3.5× la cible spec : `moc-index.md` est lourd (470 tok à lui seul). **Adressé en v2 (voir ci-dessous).**

---

## v2 — Compression moc-index + tags-list MOCs (commit 2026-04-13 21:50)

**Changements :**
- `moc-index.md` : table verbose 4-col (Scope/Notes/Quand l'utiliser) → table compacte pipe 4-col (`MOC | tags | n | use_when`)
- 8 MOCs : ajout `tags: [list]` dans frontmatter (3-5 tags par MOC, dominant en premier)
- `.nightly-prompt.md` : spec format compact pour cohérence multi-cycle nightly
- `/load-moc` skill : prose alignée sur match tags + use_when (vs scopes)

**Sizing post-v2 :**

| Asset | v1 (B → tok) | v2 (B → tok) | Δ |
|-------|--------------|--------------|---|
| `moc-index.md` | 1883 → ~470 | 939 → **~234** | **-50%** |
| `moc-architecture.md` (target MOC) | 1528 → ~382 | 1569 → ~392 | +2% (tags ajoutés) |
| **Scenario 1 solo (index + 1 MOC)** | 1180 tok | **627 tok** | **-47%** |
| **Scenario 2 multi (index + 2 MOCs)** | n/a | **668 tok** | — |

**Routing accuracy validé sur 2 queries simulées :**
- "Pourquoi Anthropic Batch?" → tag `architecture` + use_when "comment/pourquoi" → `moc-architecture` ✅
- "crash nightly cron" → tags `nightly,cron` + sémantique "crash"→`bug` → `moc-anti-bug` + `moc-nightly-agent` (multi-MOC) ✅

**Verdict v2 :** Cible spec "340 tok/query" toujours non atteinte (627 vs 340), mais réduction massive (-47%) sans perte de routing accuracy. Pour atteindre 340 tok il faudrait basculer vers un JIT moc-routing skill (plus lourd à designer, prévu en v3 si besoin).

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
