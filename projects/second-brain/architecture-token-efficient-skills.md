---
status: accepted
type: architecture-decision
created: 2026-04-13
tags: [decision, architecture, skills, tokens, cost-efficiency, ADR]
domain: second-brain
deciders: [djemild]
---

# ADR — Design token-efficient pour les skills custom

> **Décision** : les skills custom (`/resume-session`, `/nightly-triage`, `/sprint-task-tracker`) suivent un pattern strict de token-efficiency basé sur le shell-first pre-processing.
> **Date** : 2026-04-13
> **Statut** : Accepted (Phase 3 audit implementation)

## Contexte

Après audit du setup Claude Code (2026-04-13), 3 workflows récurrents ont été identifiés comme candidats à l'automation via skills :
1. Rituel "où on en est" début de session (~2000 tokens manuel)
2. Diagnostic matinal du nightly run (~1500 tokens manuel)
3. Tracking progression Sprint task-ids ↔ git log (~1000 tokens manuel)

Total quotidien sans skills : ~4500 tokens/jour de priming.
Avec skills bien designés : ~1200 tokens/jour (≈70% économie).

## Les 5 principes token-efficient

### Principe 1 — Shell-first pre-processing
**Toutes les extractions doivent se faire en bash AVANT que le LLM voit le résultat.**

| ❌ Anti-pattern | ✅ Pattern |
|-----------------|------------|
| `Read(_logs/last-nightly.json)` | `jq '{status, last_run}' _logs/last-nightly.json` |
| `Read(maintenance-report.md)` | `grep -E "^#.*(ALERT\|🚨)" _logs/maintenance-report.md \| head -10` |
| `Read(nightly-agent.log)` | `tail -20 _logs/nightly-agent.log \| grep ERROR \| head -5` |

**Gain** : 5-50× moins de tokens quand le fichier source est gros.

### Principe 2 — Champs précis, pas de dump complet
Pour JSON : **toujours `jq` avec sélection de champs explicite**.

```bash
# ❌ Mauvais : dump complet
jq '.' _logs/last-nightly.json   # 25 lignes output

# ✅ Bon : champs précis
jq '{status, last_run, notes_added}' _logs/last-nightly.json   # 4 lignes output
```

### Principe 3 — Sortie structurée minimale
Le skill doit **prescrire le format de sortie final** (tableau markdown, bullet points) — **pas de prose**.

| ❌ Prose | ✅ Tableau |
|----------|------------|
| "The nightly run completed successfully yesterday at..." | `\| Nightly \| ✅ \| 2026-04-12 03:17 \|` |
| "There are 9 broken wikilinks that need attention..." | `\| Broken links \| 9 \| (5 premiers ci-dessous) \|` |

### Principe 4 — Budget tokens par skill, déclaré et respecté
Chaque skill déclare son **budget cible** dans le frontmatter (`description: ~400 tokens`).

Si un skill dépasse systématiquement sa cible → réduire les sources OU ajouter un flag `--verbose`.

### Principe 5 — `allowed-tools` restreint
Limiter chaque skill aux tools nécessaires — **empêche le LLM de re-lire des fichiers complets par réflexe** :

```yaml
allowed-tools: Bash(jq:*), Bash(grep:*), Bash(wc:*), Bash(head:*), Bash(tail:*)
```

Notable : **pas de `Read`** → force le LLM à passer par bash pour extraire.

## Pattern d'implémentation

### Structure type d'un skill token-efficient

```markdown
---
description: <one-liner avec budget tokens cible>
allowed-tools: Bash(<commandes précises>)
argument-hint: "<arg optionnel>"
---

# /nom-skill — <objectif en 1 ligne>

## Règles absolues

1. JAMAIS dumper <fichier volumineux>
2. Toujours extraire via jq/grep/head
3. Sortie = format strict (cf. section dédiée)

## Exécuter dans cet ordre précis

\`\`\`bash
# Commande 1 — source de vérité 1 (coût: X bytes)
jq '{champ1, champ2}' source.json

# Commande 2 — source de vérité 2
grep -E 'pattern' source.md | head -N
\`\`\`

## Format de sortie attendu

\`\`\`markdown
## 🎯 Titre skill

| Métrique | Valeur | Détail |
|----------|--------|--------|
| ... | ... | ... |

## Actions priorisées
1. ...
\`\`\`

## Priorisation / logique métier

<Règles de priorisation spécifiques au skill>

## Ne JAMAIS
- ...
```

## Mesures sur les 3 skills créés (2026-04-13)

### `/resume-session`
- **Budget cible** : ~400 tokens
- **Output réel mesuré** : ~650 bytes ≈ 200 tokens (ratio ~3.25 chars/token en français/UTF-8)
- **Économie vs manuel** : 2000 → 200 tokens (**90%**)
- **Sources** : git log, git status count, jq last-nightly, jq nlm-status, grep tech-debt, find -mtime

### `/nightly-triage`
- **Budget cible** : ~500 tokens
- **Output réel mesuré** : ~1100 bytes ≈ 340 tokens
- **Économie vs manuel** : 1500 → 340 tokens (**77%**)
- **Sources** : jq last-nightly, jq nlm-status, grep maintenance-report, wc broken-links, tail nightly-agent.log

### `/sprint-task-tracker`
- **Budget cible** : ~400 tokens
- **Output réel mesuré** : ~800 bytes ≈ 250 tokens
- **Économie vs manuel** : 1000 → 250 tokens (**75%**)
- **Sources** : ls plans, grep task-ids, git log --grep, git log non-tagged

**Total économie quotidienne** : ~3700 tokens (si les 3 skills sont utilisés 1×/jour chacun).

**Note méthodologique** : ratio bytes→tokens estimé à ~3.25 chars/token pour le français en UTF-8 (vs ~4 pour anglais ASCII). Pour mesure exacte, utiliser `tiktoken` ou `anthropic.count_tokens()`.

## Traps à éviter

### Trap 1 — `xargs` + `head` → signal 13 (SIGPIPE)
```bash
# ❌ find | xargs basename | head  → signal 13 warnings
find . -name "*.md" | xargs -I{} basename {} | head -5

# ✅ find | sed | head  → pipe-safe
find . -name "*.md" | sed 's|.*/||' | head -5
```

### Trap 2 — `Read` tool dans allowed-tools
Si `Read` est autorisé, le LLM ira re-lire les fichiers par réflexe. **Exclure `Read`** force le shell-first.

### Trap 3 — Prose générée par le LLM
Même avec du shell-first, le LLM peut noyer le résultat dans de la prose.
**Solution** : préciser "format strict" + "zéro phrase marketing" dans les règles absolues.

### Trap 4 — Skill trop générique
Un skill "check everything" qui lit 20 fichiers échoue l'audit token.
**Solution** : 1 skill = 1 workflow précis. Ne pas consolider.

## Règles de création d'un nouveau skill token-efficient

1. **Mesurer le coût manuel** actuel (combien de reads, quelle taille totale)
2. **Identifier les sources de vérité précises** (fichiers + champs nécessaires)
3. **Pour chaque source** : choisir extraction shell (`jq`, `grep`, `head`, `wc`)
4. **Budget cible** : viser ≤ 30% du coût manuel
5. **Tester manuellement** la commande shell avant d'écrire le skill
6. **Format de sortie** : tableau markdown strict
7. **allowed-tools** : whitelist stricte, pas de `Read` sauf nécessité

## Liens
- [[audit-setup-claude-code-2026-04-13]] — audit source qui a identifié les 3 skills
- [[decision-bash-vs-python-boundary]] — règles bash/python du projet
- [[tech-debt-registry]] — registry des dettes techniques

## Tags
#architecture #skills #tokens #cost-efficiency #decision #ADR
