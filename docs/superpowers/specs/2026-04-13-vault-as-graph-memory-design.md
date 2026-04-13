# Vault-as-Graph-Memory — Design Spec

**Date** : 2026-04-13
**Status** : Approved (brainstorming phase) — ready for implementation plan
**Author** : Djemil + Claude (Opus 4.6)
**Target** : Refonte totale de l'architecture de mémoire persistante cross-session

---

## 1. Context

### Problème observé

L'utilisateur expérimente **14% de consommation de session au boot** (~28 000 tokens sur 200K) lors de chaque reprise de session Claude Code. Un audit avec 4 agents Opus en parallèle a révélé :

1. **Le timeline priming claude-mem** (~11 800 tokens) — hook SessionStart qui injecte les 50 observations récentes **systématiquement**
2. **Memory files redondants** (~5 280 tokens) — dupliquent 48% du contenu du vault Obsidian
3. **Chroma indexé mais inutilisé** — 24MB d'embeddings vectoriels construits mais `SEMANTIC_INJECT=false` (anti-pattern pur)
4. **Anti-pattern "memory-as-scratchpad"** — `session-state-2026-04-12.md` périme à J+1
5. **Architecture level 2023** — claude-mem v12 reste en "dump top-N" vs progressive disclosure 2026

### Insight architectural

**Le vault Obsidian EST déjà un knowledge graph** :
- 43+ notes actives avec frontmatter YAML typé (`type: decision`, `type: discovery`, etc.)
- Wikilinks `[[note-X]]` = edges natifs du graphe
- 8 MOCs (Maps of Content) auto-générés dans `_meta/moc/*.md` par le nightly agent
- Backlinks Obsidian = graph traversal bidirectionnel

Les 4 agents d'audit ont manqué ce point car leur training couvre les memory frameworks génériques (MemGPT, mem0, Letta, Zep) — pas les vaults Obsidian comme systèmes de mémoire.

---

## 2. Goals & Non-Goals

### Goals

- **G1** : Réduire le boot cost de **14% → 0.25%** (28K → ~500 tokens)
- **G2** : Éliminer la duplication memory files ↔ vault (0% de duplication target)
- **G3** : Exploiter les MOCs existants comme entry points du graph traversal
- **G4** : Utiliser le LLM lui-même comme retriever sémantique (zéro infra supplémentaire)
- **G5** : Activer Chroma (déjà indexé) en fallback lazy pour queries fuzzy
- **G6** : Rester 100% cohérent avec la décision `[[decision-knowledge-graph-deferred]]` existante

### Non-Goals

- **NG1** : Pas de knowledge graph externe (Zep/Cognee/Neo4j) — wikilinks Obsidian suffisent
- **NG2** : Pas de rebuild de pipeline embedding custom — Chroma existant suffit
- **NG3** : Pas de migration progressive — big bang validé (toutes les infos sont dans le vault)
- **NG4** : Pas de suppression de claude-mem — désactivation au boot seulement, historique préservé via MCP search
- **NG5** : Pas d'UserPromptSubmit hook avec embedding auto — coût à chaque prompt gaspille
- **NG6** : Pas de migration de la CLAUDE.md auto-memory system — on travaille DANS ce système

---

## 3. Architecture — Option E+ "Vault-as-Graph-Memory"

### 3.1 Vue d'ensemble — 5 couches

```
┌─────────────────────────────────────────────────────────────┐
│ BOOT — ~500 tokens (0.25% de 200K)                           │
│                                                               │
│ ┌─ COUCHE 0: Memory Tool natif (~200 tokens) ────────────┐  │
│ │  user_profile.md  — role, stack, workflow (10 lignes)   │  │
│ │  session_pointer.md — branche, goal courant (5 lignes)  │  │
│ └──────────────────────────────────────────────────────────┘  │
│                                                               │
│ ┌─ COUCHE 1: Skills metadata (~300 tokens) ──────────────┐  │
│ │  /resume-session, /nightly-triage, /sprint-task-tracker │  │
│ │  /load-moc (NEW)  /tech-debt-status (NEW option)        │  │
│ └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                        │ lazy on demand
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ COUCHE 2: Vault MOCs (~100-300 tokens par MOC chargé)        │
│   _meta/moc/moc-index.md (NEW master — routing)             │
│   _meta/moc/moc-{topic}.md (8 existants + nouveaux)         │
└─────────────────────────────────────────────────────────────┘
                        │ follow wikilinks
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ COUCHE 3: Vault notes (lazy par note, ~300-500 tokens)       │
│   projects/second-brain/*.md (43+ notes)                    │
│   universal/*.md                                             │
│   Filtering via frontmatter: grep 'type: decision', etc.     │
└─────────────────────────────────────────────────────────────┘
                        │ fallback quand MOC miss
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ COUCHE 4: claude-mem search-only (historique, lazy)          │
│   mcp__claude-mem__search(query) → Chroma top-k             │
│   mcp__claude-mem__timeline, get_observations               │
│   SessionStart injection DÉSACTIVÉE                          │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Couche 0 — Memory Tool natif (`memory_20250818`)

**Scope** : uniquement le minimum viable qui **n'est pas** dans le vault.

#### `user_profile.md` (~100 tokens)
```markdown
# User Profile

- Role: Senior dev solo (macOS, zsh)
- Stack: Python 3.9+, Bash, Obsidian, Claude Code
- Workflow: Second Brain pipeline (vault + nightly agent + NotebookLM)
- Preferences:
  - Token-efficient skills (shell-first pre-processing)
  - Bash vs Python boundary: cf. [[decision-bash-vs-python-boundary]]
  - Testing: TDD avec pytest (52 tests actifs)
- Security: secrets en macOS Keychain (pas de .env)
```

#### `session_pointer.md` (~100 tokens, auto-updated)
```markdown
# Session Pointer

- Branche courante: <auto via Stop hook>
- Dernier commit: <auto via Stop hook>
- Goal actuel: <one-liner user peut éditer>
- MOCs fréquemment touchés: <top-3 auto>
```

**Total couche 0** : ~200 tokens fixes au boot.

### 3.3 Couche 1 — Skills (progressive disclosure)

**Skills existants (gardés)** :
- `/resume-session` (300 tok, context matinal)
- `/nightly-triage` (400 tok, diagnostic logs)
- `/sprint-task-tracker` (300 tok, progression sprints)

**Skills à créer** :
- `/load-moc <topic>` — retrieval 2-tiers (voir 3.6)
- `/tech-debt-status` (optionnel) — requête focalisée sur `tech-debt-registry.md`

**Boot cost skills** : metadata-only (~300 tokens pour les 5 skills listés).

### 3.4 Couche 2 — Vault MOCs

**MOCs existants** (générés par nightly agent LLM, `.nightly-prompt.md:425`) :
- `moc-second-brain.md` — principal (27 notes)
- `moc-architecture.md` — décisions archi (12 notes)
- `moc-decision.md`, `moc-discovery.md`, `moc-anti-bug.md`
- `moc-nightly-agent.md`, `moc-security.md`, `moc-gpparts.md`

**MOC à créer** : `moc-index.md` (master routing)

**Format MOCs amélioré** (avec frontmatter YAML) :
```yaml
---
type: moc
tag: architecture
notes_count: 12
last_updated: 2026-04-13
scope: "Architecture decisions, patterns, and pipeline design"
parent_moc: second-brain
---
# MOC — #architecture
Generated: 2026-04-13 | 12 notes

- [[note-X]] — description dense 1 ligne
...
```

### 3.5 Couche 3 — Vault notes (leaves du graph)

**Aucun changement sur les notes elles-mêmes.** Seulement comportement d'accès :
- Read via skills (jamais au boot)
- Filtering via `grep 'type: X'` sur frontmatter
- Follow wikilinks depuis MOCs

### 3.6 Couche 4 — claude-mem search-only

**Reconfiguration** :
```
CLAUDE_MEM_CONTEXT_OBSERVATIONS=0      # plus d'injection boot (était 50)
CLAUDE_MEM_SHOW_LAST_SUMMARY=false     # plus de session summary boot
CLAUDE_MEM_SEMANTIC_INJECT=false       # reste désactivé boot
CLAUDE_MEM_CHROMA_ENABLED=true         # reste true pour MCP search
```

**Accès uniquement via MCP tools** :
- `mcp__claude-mem__search(query)` — Chroma cosine top-k
- `mcp__claude-mem__timeline` — historique temporel
- `mcp__claude-mem__get_observations(ids)` — facts ponctuels

---

## 4. Data flow — Exemples concrets

### 4.1 Boot d'une nouvelle session

```
Claude Code startup
  ├─ Auto-load Memory Tool files (~200 tok)
  │    user_profile.md + session_pointer.md
  ├─ Skills registry metadata (~300 tok, names + 1-line desc)
  └─ Zero injection claude-mem (désactivé)

Total boot context = ~500 tokens (vs ~28K aujourd'hui)
```

### 4.2 Query simple ("comment gérer bash vs python ?")

```
User prompt arrives
  ├─ Claude reads Memory Tool user_profile.md
  │    → voit pointer [[decision-bash-vs-python-boundary]]
  ├─ Claude Read directly the vault note (~500 tok)
  └─ Answer with citation

Total = ~500 tokens (direct hit via Memory Tool pointer)
```

### 4.3 Query sur topic inconnu ("comment on évite crashes nightly ?")

```
User prompt arrives
  ├─ Claude invokes /load-moc "crash nightly"
  │    ├─ Tier 1: Read moc-index.md (~100 tok)
  │    │    Claude reasoning: "nightly + crash → moc-nightly-agent + moc-anti-bug"
  │    ├─ Read moc-nightly-agent.md (~80 tok)
  │    └─ Read moc-anti-bug.md (~150 tok)
  ├─ Claude suit 2 wikilinks pertinents
  │    Read [[anti-bug-launchd-icloud-tcc]] (~400 tok)
  │    Read [[discovery-nightly-agent-architecture]] (~600 tok)
  └─ Answer avec 2 citations

Total = ~1330 tokens (vs ~28K boot + 5-10K de re-read manuel)
```

### 4.4 Query fuzzy fallback (MOC miss)

```
User prompt: "mémoire verbose"
  ├─ Claude invokes /load-moc "mémoire verbose"
  │    ├─ Tier 1: Read moc-index.md → ambiguous
  │    └─ Tier 2: mcp__claude-mem__search("mémoire verbose")
  │         → top-5 results semantic match
  ├─ Claude picks top-2 relevant
  │    Read top-2 notes (~800 tok)
  └─ Answer

Total = ~1500 tokens (fallback sémantique)
```

### 4.5 Query historique ("qu'on a fait hier soir ?")

```
User prompt
  ├─ Claude invokes mcp__claude-mem__timeline(last_24h)
  │    → Chronological events list (~400 tok)
  ├─ Claude picks relevant events
  └─ Answer

Total = ~400 tokens (historique via MCP)
```

---

## 5. Migration plan — Big bang

**Context** : tous les memory files dupliquent du contenu déjà dans le vault (vérifié). Aucune perte d'information. Rollback facile via git.

### 5.1 Phase 1 — Nettoyage vault (30 min)

1. **Supprimer 6 fichiers iCloud conflicts** dans `_meta/moc/` : `moc-X 2.md`
2. **Commit de protection** : snapshot avant migration
3. **Vérifier** que toutes les références dans les 7 memory files existent dans le vault (script check)
4. **Créer note manquante** : `projects/second-brain/architecture-paper-synthesizer.md` (gap identifié pour `project_paper-synthesizer-pipeline`)

### 5.2 Phase 2 — Memory Tool natif setup (15 min)

1. **Identifier l'API Claude Code** pour Memory Tool natif (`memory_20250818`)
2. **Créer** `user_profile.md` (contenu validé en section 3.2)
3. **Créer** `session_pointer.md` avec template auto-update

### 5.3 Phase 3 — MOCs améliorés (1h)

1. **Créer** `_meta/moc/moc-index.md` (master routing) :
   - Format avec frontmatter YAML
   - Table scope + notes_count pour chaque MOC
2. **Ajouter frontmatter YAML** aux 8 MOCs existants
3. **Mettre à jour `.nightly-prompt.md`** pour générer/maintenir :
   - `moc-index.md` avec les MOCs existants
   - Frontmatter YAML sur tous les MOCs
   - Cap à 30 notes/MOC (sinon split thématique)
4. **Protection iCloud** : ajouter xattr `_meta/` ou le déplacer hors iCloud sync

### 5.4 Phase 4 — Skill `/load-moc` (45 min)

Créer `.claude/commands/load-moc.md` :
- Tier 1 : Read `moc-index.md` + raisonne sur le topic
- Tier 2 fallback : `mcp__claude-mem__search`
- Tier 3 fallback : `moc-second-brain.md` (master)
- Budget tokens : ~330 en moyenne

### 5.5 Phase 5 — Claude-mem reconfiguration (15 min)

Modifier `~/.claude-mem/settings.json` :
```json
{
  "CLAUDE_MEM_CONTEXT_OBSERVATIONS": 0,
  "CLAUDE_MEM_SHOW_LAST_SUMMARY": false,
  "CLAUDE_MEM_SEMANTIC_INJECT": false,
  "CLAUDE_MEM_CHROMA_ENABLED": true
}
```

Vérifier que `mcp__claude-mem__search` reste exposé.

### 5.6 Phase 6 — Suppression memory files legacy (big bang)

Après validation des couches 0-3 en dry-run :
```bash
cd ~/.claude/projects/-Users-djemildavid-Documents-Obsidian-KnowledgeBase/memory
rm project_audit-2026-04-13.md
rm project_bash-vs-python-rules.md
rm project_future-managed-agents.md
rm project_paper-synthesizer-pipeline.md
rm project_second-brain-architecture-v5.md
rm project_session-state-2026-04-12.md
rm project_skills-custom.md
# Réécrire MEMORY.md en pointer minimal (~3 lignes) :
cat > MEMORY.md <<EOF
# Memory Index
Migration to Vault-as-Graph-Memory 2026-04-13.
See: user_profile.md, session_pointer.md, or /load-moc <topic>
EOF
```

**Rollback** : `git checkout HEAD~1 -- ~/.claude/projects/.../memory/` (le dossier memory est versionné).

Wait — il n'est PAS versionné par défaut (il est dans `~/.claude`, pas dans le vault). **Action supplémentaire** : backup manuel avant suppression :
```bash
tar czf /tmp/memory-backup-2026-04-13.tar.gz ~/.claude/projects/-Users-djemildavid-Documents-Obsidian-KnowledgeBase/memory/
```

### 5.7 Phase 7 — Validation + mesure (30 min)

1. **Redémarrer Claude Code** (session fresh)
2. **Mesurer boot cost** (inspection du context injecté)
3. **Comparer** : cible < 1000 tokens au boot (vs 28K avant)
4. **Tester 5 scenarios** :
   - Query simple (pointer direct)
   - Query topic connu (via MOC)
   - Query topic inconnu (fallback embedding)
   - Query historique (claude-mem search)
   - Query "où on en est" (skill `/resume-session`)

---

## 6. Validation metrics

| Métrique | Baseline | Target | Acceptable |
|----------|----------|--------|------------|
| Boot cost (tokens) | 28 000 | ~500 | < 2 000 |
| Boot cost (%) | 14% | 0.25% | < 1% |
| Memory files count | 8 | 0 (or MEMORY.md minimal) | ≤ 2 |
| Duplication vault ↔ memory | 48% | 0% | 0% |
| Retrieval moyen par query | N/A | ~350 tokens | < 1000 tokens |
| Boot latency | 2-3s | < 1s | < 2s |

---

## 7. Risks & Mitigations

### R1 — MOC index corruption par nightly
**Risque** : si `.nightly-prompt.md` a un bug, `moc-index.md` devient incohérent.
**Mitigation** :
- Version control des MOCs (déjà dans vault git)
- Test `moc-index.md` parsing dans `integrity_check.py`
- Fallback `moc-second-brain.md` si `moc-index.md` missing

### R2 — Memory Tool natif indisponible
**Risque** : la beta API `memory_20250818` casse ou change.
**Mitigation** :
- Fallback vers minimal MEMORY.md (ancien mécanisme) pour user_profile + session_pointer
- Les 2 fichiers font ~200 tokens, acceptable comme bas de gamme

### R3 — Chroma corrompu
**Risque** : l'index HNSW claude-mem peut se corrompre.
**Mitigation** :
- Tier 2 (embeddings) est déjà marqué "fallback" — si Chroma down, Claude saute à Tier 3 (master MOC)
- Rebuild Chroma possible via `mcp__claude-mem__rebuild_corpus`

### R4 — Conflits iCloud récurrents sur `_meta/`
**Risque** : malgré nettoyage, nouveaux conflits possibles.
**Mitigation** :
- Ajouter alerting dans `integrity_check.py` (déjà détecte conflits)
- Protection xattr `_meta/` comme `_work.nosync` (extension de TD-2026-XXX)
- Option radicale : déplacer `_meta/` hors iCloud via symlink

### R5 — Skill `/load-moc` mal routé
**Risque** : Claude charge le mauvais MOC, retrieval inefficace.
**Mitigation** :
- Auditable : Claude explique son choix
- Iteration possible : user peut dire "non, charge plutôt moc-X"
- Tier 2 fallback compense

### R6 — Régression vs workflow actuel
**Risque** : certaines infos "utiles" dans les memory files actuels manquent au début.
**Mitigation** :
- Backup tar.gz avant suppression
- Rollback en 1 commande si besoin
- Phase 7 validation couvre 5 scenarios critiques

---

## 8. Open questions (pour writing-plans)

### OQ1 — Memory Tool natif : API exacte ?
**Question** : `memory_20250818` est un tool officiel Anthropic mais son activation via Claude Code CLI n'est pas 100% documentée. À vérifier :
- Comment l'activer dans `settings.json` ?
- Les fichiers `user_profile.md` vont où (vault, `~/.claude/memory/`, autre) ?
- Compatibilité avec `auto-memory` de Claude Code ?

**Plan d'action** : recherche dans docs Anthropic + tests lors de l'implémentation.

### OQ2 — Auto-update du `session_pointer.md`
**Question** : par quel hook ? (Stop hook probablement, mais user veut pas de délai end-of-session).
- Option A : Stop hook écrit branche + last commit
- Option B : hook UserPromptSubmit écrit à chaque prompt (trop fréquent)
- Option C : skill `/pin-session-goal "goal"` — user-driven only

**Plan d'action** : choisir au moment de l'implémentation, probable C + A minimal.

### OQ3 — Cap sur MOCs
**Question** : quand split un MOC > 30 notes en sous-MOCs ?
**Plan d'action** : règle dans `.nightly-prompt.md` à préciser.

---

## 9. Success criteria

La refonte est **réussie** si :

- ✅ Boot cost < 1000 tokens mesurables (cible 500)
- ✅ `/resume-session`, `/nightly-triage`, `/sprint-task-tracker` fonctionnent inchangés
- ✅ Nouveau `/load-moc <topic>` retourne la bonne info en < 1000 tokens pour les 5 scenarios de validation
- ✅ Aucune perte d'info critique après big bang (validation user sur 3 queries "est-ce que tu te souviens de X")
- ✅ Rollback possible en 1 commande
- ✅ 0 duplication memory ↔ vault

---

## 10. Next steps

Après approval de ce spec par user :
1. **Writing-plans skill** : génération du plan d'implémentation détaillé avec TDD + subtasks 2-5 min
2. **Implementation** : exécution du plan (subagent-driven development ou direct)
3. **Validation Phase 7** : mesure réelle vs targets
4. **Iteration** : ajustement prompts + configs selon mesures

---

## Annexes

### A1 — Cohérence avec décisions existantes

- `[[decision-knowledge-graph-deferred]]` : spec respecte la décision (pas de KG externe, wikilinks suffisent)
- `[[decision-architecture-hybride-second-brain]]` : architecture hybride maintenue
- `[[decision-bash-vs-python-boundary]]` : skill `/load-moc` respect règles bash/python

### A2 — Mapping vers état de l'art 2026

| Système 2026 | Concept utilisé dans Option E+ |
|--------------|--------------------------------|
| Anthropic Memory Tool natif | Couche 0 (user_profile, session_pointer) |
| Claude Skills progressive disclosure | Couche 1 (metadata only au boot) |
| MOCs Obsidian (Nick Milo) | Couche 2 (entry points graph) |
| Graph-based retrieval (Zep/Graphiti) | Couche 3 — via wikilinks Obsidian natifs |
| mem0 extract/update/retrieve | Couche 4 — via claude-mem MCP search |
| LLM-as-retriever (HippoRAG insight) | Tier 1 routing (gratuit) |
| Hybrid RAG (BM25 + vector) | Tier 2 fallback via Chroma |

### A3 — Références
- [[audit-setup-claude-code-2026-04-13]]
- [[tech-debt-registry]]
- [[decision-knowledge-graph-deferred]]
- `.nightly-prompt.md:425` (génération MOCs)
- `~/.claude-mem/settings.json` (config claude-mem)
