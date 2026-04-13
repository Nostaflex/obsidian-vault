---
status: audit-complete
priority: high
created: 2026-04-13
tags: [audit, claude-code, skills, plugins, setup, security]
domain: second-brain
type: audit
auditors: [opus-agent-inventory, opus-agent-market, opus-agent-pipeline]
---

# Audit complet — Setup Claude Code Second Brain

> **Date** : 2026-04-13
> **Méthode** : 3 agents Opus dispatchés en parallèle (inventaire local, marché 2026, fit pipeline-specific)
> **Verdict global** : **B+** — top 5% des setups power users, mais 3 urgences sécurité + redondances à nettoyer

---

## 📊 Synthèse executive

| Axe | Score | Détail |
|-----|-------|--------|
| **Alignement marché** | ✅ A | superpowers + claude-mem = duo dominant 2026 |
| **Sécurité** | 🚨 D | 3 secrets en clair, permissions trop larges |
| **Cohérence skills** | ⚠️ B- | 5 redondances, stubs cassés |
| **Fit pipeline** | ⚠️ C | Workflows quotidiens sans skill dédié |
| **Dette technique** | ⚠️ C | Voir [[tech-debt-registry]] |

---

## A. 🚨 URGENT — Fuites de sécurité

### Fuite #1 — GitHub PAT en clair
**Fichier** : `~/.claude/settings.json` lignes 3-4
```
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_REDACTED_xxxxxxxxxxxxxxxxxxxx
GITHUB_TOKEN=ghp_REDACTED_xxxxxxxxxxxxxxxxxxxx  # duplicat
```

**Action requise** :
- [ ] Révoquer sur github.com/settings/tokens
- [ ] Générer nouveau token avec scopes minimaux
- [ ] Stocker en keychain macOS : `security add-generic-password -a djemildavid -s github-pat -w <nouveau_token>`
- [ ] Dans `~/.zshrc` : `export GITHUB_TOKEN="$(security find-generic-password -a djemildavid -s github-pat -w)"`
- [ ] Purger `~/.claude/backups/` (contient probablement l'ancien token)

### Fuite #2 — 2 Google API Keys en clair
**Fichier** : `.claude/settings.local.json` ligne 47-48
```
AIzaSy_REDACTED_oldkey
AIzaSy_REDACTED_newkey
```

**Action requise** :
- [ ] Révoquer sur console.cloud.google.com/apis/credentials
- [ ] Générer nouvelles clés avec restrictions IP/API
- [ ] Sortir du repo (settings.local.json) → keychain ou `.env` git-ignored
- [ ] Auditer les commits : `git log --all -p | grep "AIzaSy"` pour vérifier si déjà committé

### Fuite #3 — Permissions trop larges
```
Read(//Users/djemildavid/**)          # accès home entier
Read(//Users/djemildavid/.claude/**)  # accès config Claude entière
Bash(python3)                          # python arbitraire
Bash(python3 -c ':*)                   # exécution inline
Bash(pip3 install:*)                   # installation paquets sans garde
Bash(brew install:*)                   # installation brew sans garde
```

**Action** : remplacer par des globs ciblés :
- `Read(/Users/djemildavid/Documents/Obsidian/**)`
- `Bash(python3 paper_synthesizer.py:*)`
- `Bash(python3 corpus_collector.py:*)`
- `Bash(python3 -m pytest:*)`
- Supprimer les Bash(pip3/brew install) — exigences manuelles avant

---

## B. 🧹 Redondances à nettoyer

| Plugin/Skill | Doublon avec | Action |
|--------------|--------------|--------|
| `feature-dev` | `superpowers:writing-plans` | 🗑️ Désinstaller |
| `code-review` | `superpowers:requesting-code-review` | 🗑️ Désinstaller |
| `claude-mem:make-plan` | `superpowers:writing-plans` | ⚠️ Choisir un axe |
| `claude-mem:do` | `superpowers:executing-plans` | ⚠️ Choisir un axe |
| `playwright` plugin (24 MCP tools) | Jamais utilisé | 🗑️ Désinstaller |
| `deprecated` stubs superpowers (`write-plan`, `execute-plan`, `brainstorm`) | Nouveaux: `writing-plans`, etc. | 🗑️ Cachés |

**Gain** : réduit la pollution du namespace de skills + -24 tools playwright en contexte.

---

## C. 🐛 Bugs silencieux trouvés

### Bug #1 — `/notebooklm-weekly` cassé (stub 1 ligne)
**Fichier** : `.claude/commands/notebooklm-weekly.md`
**Contenu actuel** : `# Skill: NotebookLM Weekly Synthesis` (juste un titre, vide)

**Conséquence** : la slash command ne fait rien → explique pourquoi elle traîne en "prochain geste" dans la memory depuis plusieurs jours.

**Action** : implémenter le skill complet (référencer `notebooklm_weekly.py`, setup auth, flow hebdo).

### Bug #2 — MCP `obsidian-vault` mal configuré
**Config actuelle** (dans `~/.claude/mcp.json`) pointe vers :
```
/var/folders/.../tmp.hdWpzdR59A/
```
Au lieu de `/Users/djemildavid/Documents/Obsidian/KnowledgeBase/`.

**Hypothèse** : soit symlink oublié, soit config obsolète d'un worktree éphémère. Les Read passent par l'outil natif en fallback (d'où les 80+ `Read(//Users/djemildavid/Documents/Obsidian/**)` dans settings).

**Action** : soit corriger le path, soit désinstaller le MCP et passer au remplaçant communautaire [obsidian-mcp-server](https://github.com/MarkusPfundstein/mcp-obsidian) (3k+ stars, full read/write/search).

---

## D. 🎯 Top 3 skills custom à créer (Quick Wins)

Agent pipeline-specific : "Ne construis que ces 3, utilise 2 semaines, puis itère."

### Skill #1 — `/resume-session` (~30 min, HIGH impact)
**Problème** : rituel manuel de 3-4 reads à chaque nouvelle session.

**Design** :
```
/resume-session
→ glob dernier project_session-state-*.md
→ tail _meta/LOG.md
→ git log -5 + git status + branche
→ cat _logs/last-nightly.json | jq '.enrichment_status'
→ résumé 200 tokens : "où on en est + prochain geste"
```

**ROI** : économise ~2000 tokens de priming × session × jour.

### Skill #2 — `/nightly-triage` (~30 min, HIGH impact)
**Problème** : chaque matin, grep manuel dans 5 fichiers `_logs/*`.

**Design** :
```
/nightly-triage
→ jq _logs/last-nightly.json (schéma v6)
→ check _logs/nlm-status.json (ALERT-nlm-degraded ?)
→ wc -l _logs/broken-links.txt + conflicts.txt
→ Décisions priorisées : fix link / archive orphan / quarantine paper / retry nlm
```

**ROI** : 10-15 min/matin économisées.

### Skill #3 — `/sprint-task-tracker` (~45 min, HIGH impact)
**Problème** : les task-ids BS-1, BS-2, F9, F22... tracés à la main entre plan et `git log`.

**Design** :
```
/sprint-task-tracker <sprint-file.md>
→ regex extraction des task-ids du plan
→ git log --grep="BS-\|F[0-9]" depuis date du plan
→ Tableau : [x] BS-1 — commit 57fb24f / [ ] BS-3 — non commité
→ Détection items orphelins (commits sans task-id)
```

**ROI** : zéro oubli, visibilité instantanée du % de sprint fait.

---

## E. 📈 Tendances 2026 à adopter

### Tendance #1 — `ultrathink` **DÉPRÉCIÉ** → Adaptive Thinking
Claude 4.6 détermine auto la profondeur. Workflow canonique :
**EXPLORE → PLAN (adaptive) → CODE → COMMIT**
Source : [decodeclaude.com](https://decodeclaude.com/ultrathink-deprecated/)

### Tendance #2 — Post-Compaction Hooks
Buffer passé de 45k→33k tokens début 2026 (non annoncé).
Ajouter section `## Compact Instructions` dans `CLAUDE.md` pour survivre aux compactions.
Source : [Nick Porter Medium](https://medium.com/@porter.nicholas/claude-code-post-compaction-hooks-for-context-renewal-7b616dcaa204)

### Tendance #3 — Skills 2.0 Eval-Driven
Nouveau `skill-creator` Anthropic embarque benchmarks (train/test 60/40, précision trigger + qualité output).
Source : [claude.com/blog/improving-skill-creator](https://claude.com/blog/improving-skill-creator-test-measure-and-refine-agent-skills)

### Tendance #4 — Skills research tendance (fit fort)
- **[Deep-Research-skills](https://github.com/Weizhena/Deep-Research-skills)** — PRISMA + arXiv/S2
- **[claude-scientific-skills](https://github.com/K-Dense-AI/claude-scientific-skills)** — 31 skills full lifecycle
- **[ARIS (Auto-Research-In-Sleep)](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep)** — **fit direct avec ton nightly-agent**
- **[obsidian-mcp-server](https://github.com/MarkusPfundstein/mcp-obsidian)** — remplacer l'actuel cassé

---

## F. 💎 Opportunités de publication

Ton setup a **3 patterns originaux** sous-représentés dans le marché :

1. **EU-compliance fallback** (Gemini bloqué → Anthropic Batch, F22) — **zéro skill existant**
2. **INDEX diff + vault health checks** (BS-4/BS-5/F9) — pattern publiable
3. **Paper synth non-blob** (concepts atomiques vs digests) — doctrine sous-représentée

→ Future marketplace envisageable : `djemild/second-brain-skills`

---

## G. 🚀 Plan d'action priorisé

### Phase 1 — Aujourd'hui (urgence, 30 min)
- [ ] Révoquer GitHub PAT + 2 Google API keys
- [ ] Rotation + keychain/env vars
- [ ] Purger `~/.claude/backups/`

### Phase 2 — Cette semaine (nettoyage, ~1h)
- [ ] Désinstaller `feature-dev`, `code-review`, `playwright`
- [ ] Choisir axe plan/execute (superpowers OU claude-mem)
- [ ] Fixer `/notebooklm-weekly` (stub vide)
- [ ] Vérifier / fixer MCP obsidian-vault path
- [ ] Resserrer permissions dans settings

### Phase 3 — Semaine prochaine (quick wins, ~2h)
- [ ] Créer `/resume-session`
- [ ] Créer `/nightly-triage`
- [ ] Créer `/sprint-task-tracker`
- [ ] Utiliser 2 semaines → itérer / prioriser le lot suivant

### Phase 4 — Fin avril (tendances, optionnel)
- [ ] Ajouter `## Compact Instructions` dans `CLAUDE.md`
- [ ] Évaluer un skill research (ARIS ou claude-scientific-skills)
- [ ] Remplacer MCP obsidian-vault par obsidian-mcp-server communautaire

### Phase 5 — Q2 2026 (long terme)
- [ ] Considérer [[future-managed-agents-anthropic|Managed Agents]] pour nightly cloud
- [ ] Publier les 3 patterns originaux en marketplace

---

## H. Skills sous-utilisés (usage nul/faible)

| Skill | Plugin | Raison |
|-------|--------|--------|
| `claude-mem:knowledge-agent` | claude-mem | Conçu pour dev plugins, pas Second Brain |
| `claude-mem:timeline-report` | claude-mem | Jamais appelé dans logs |
| `claude-mem:version-bump` | claude-mem | Pour dev plugins, pas pipeline |
| `claude-mem:smart-explore` | claude-mem | Tree-sitter AST inadapté au Markdown |
| `playwright:*` (24 tools) | playwright | Jamais utilisé pour Second Brain |
| `feature-dev:feature-dev` | feature-dev | Doublon superpowers |

---

## I. Skills actifs bien utilisés (à préserver)

- ✅ `superpowers:brainstorming` (preuves dans `.superpowers/brainstorm/`)
- ✅ `superpowers:writing-plans` + `executing-plans`
- ✅ `superpowers:test-driven-development`
- ✅ `superpowers:dispatching-parallel-agents`
- ✅ `claude-mem:mem-search` + `smart-outline` + `get_observations`
- ✅ Hooks claude-mem SessionStart/UserPromptSubmit/PostToolUse/Stop/SessionEnd
- ✅ Hook custom access-log.jsonl (scopé KnowledgeBase)
- ✅ MCP notebooklm (critique pour pipeline hebdo)

---

## Liens internes
- [[tech-debt-registry]] — dette technique détaillée
- [[future-managed-agents-anthropic]] — future implementation
- [[decision-architecture-hybride-second-brain]]
- [[architecture-dual-profile-vscode]]
- [[discovery-nightly-agent-architecture]]

## Sources agents
- Agent 1 (inventaire) : af388a80669bdeecd
- Agent 2 (marché) : a0710a81c87e1ddca
- Agent 3 (pipeline) : afc0aff044defac28

## Tags
#audit #security #tech-debt #skills #setup #future-improvements
