---
status: accepted
type: architecture-decision
created: 2026-04-13
tags: [decision, architecture, bash, python, boundary, ADR]
domain: second-brain
deciders: [djemild, opus-agent-bash-vs-python]
---

# ADR — Frontière Bash vs Python dans le Second Brain Pipeline

> **Décision** : garder le mix bash (~250 LOC) / Python (~1860 LOC testés), sans unification.
> **Date** : 2026-04-13
> **Statut** : Accepted (audit Opus)
> **Source analyse** : agent Opus a57483316c8bc224e

---

## Contexte

Le pipeline Second Brain mélange :
- **3 scripts bash** : `nightly-agent.sh` (71L), `integrity-check.sh` (134L), `corpus-rebuild.sh` (43L)
- **3 scripts Python** : `corpus_collector.py` (519L), `paper_synthesizer.py` (665L), `notebooklm_weekly.py` (681L)
- **1 suite tests** : 46 tests pytest couvrant uniquement les fichiers Python
- **Hooks Claude Code** : scripts bash courts dans `settings.json`

Question posée : faut-il tout unifier en Python ? Garder le mix ? Réécrire spécifiquement certains ?

---

## Décision

**Garder le mix actuel.** Le ratio ~250 bash / ~1860 Python est **exactement bon** pour un dev seul. Chaque langage est sur son terrain.

### Exception unique
Migrer `integrity-check.sh` → `integrity_check.py` d'ici Sprint 3 (voir [[tech-debt-registry]] TD-2026-016). C'est le seul bash qui parse du markdown structuré → fragile + non testable.

---

## Règles canoniques pour le projet

### Règle 1 — Python obligatoire quand parsing structuré
> **Toujours Python** quand le script lit/écrit du markdown, YAML, JSON ou XML structuré.

**Exemples concrets** :
- ❌ `head -1 file.md | sed 's/^# //'` (integrity-check.sh L.83-84) — casse si titre contient `#`
- ❌ `grep -o '\[\[.*\]\]' | sed ...` (integrity-check.sh L.107-110) — casse sur wikilinks multilignes, aliases `|`, ou BSD grep (macOS)
- ✅ Utiliser `pyyaml` pour frontmatter, `markdown-it-py` ou regex multilignes pour wikilinks

### Règle 2 — Bash autorisé quand glue légère
> **Toujours bash** quand le script est < 80 lignes ET appelle exclusivement des binaires système (launchd, rsync, claude CLI, git, jq).

**Exemples OK** :
- ✅ `nightly-agent.sh` (71L) — orchestrateur launchd : lock, rotation log, `claude --print`
- ✅ `corpus-rebuild.sh` (43L) — wrapper avec prompt inline pour claude CLI

### Règle 3 — Bash interdit pour les API externes
> **Jamais bash** pour appels API (Anthropic, arXiv, NotebookLM, Semantic Scholar, Gemini).

Rationale : error handling, retry, auth, circuit breaker, cache → ingérable proprement en shell.

**Statut** : ✅ déjà respecté dans le pipeline actuel.

### Règle 4 — Bash interdit si pytest nécessaire
> **Jamais bash** pour quoi que ce soit qui doive être testé unitairement.

Si la logique mérite un test → elle mérite Python. Les `tests/` couvrent uniquement les fichiers Python. Si tu sens le besoin de tester un bash, c'est qu'il doit migrer.

### Règle 5 — macOS-compatible par défaut
> **Toujours `mkdir` au lieu de `flock`** pour les locks. Toujours `command -v jq` avant d'utiliser `jq`.

Rationale :
- `flock` n'existe pas sur macOS (pas dans coreutils BSD)
- Dépendances non-portables doivent être pré-vérifiées

**Statut** : ✅ `mkdir` lock appliqué dans `nightly-agent.sh` L.17-23. ⚠️ `jq` non vérifié dans plusieurs scripts.

---

## Conséquences

### Positives
- ✅ Séparation claire des préoccupations (orchestration vs logique)
- ✅ Tests pytest continuent à couvrir ce qui a besoin d'être testé
- ✅ Portabilité Linux maintenue côté Python
- ✅ Pas de sur-ingénierie — pas d'abstraction Python par-dessus launchd

### Négatives
- ⚠️ Maintenance bicéphale : 2 environnements à déboguer (shell + pytest)
- ⚠️ Bash scripts non couverts par tests → fragilité intrinsèque
- ⚠️ Parsing MD en bash est une bombe à retardement (→ migration forcée TD-2026-016)

### Trade-offs acceptés
- On accepte de maintenir 3 fichiers bash non testés **à condition** qu'ils restent < 80 lignes et ne parsent rien de structuré.
- Si un bash dépasse 80 lignes OU commence à parser du markdown → migration Python obligatoire.

---

## Décisions associées (risques identifiés)

L'audit a révélé 3 points de fragilité dans le bash existant, loggés séparément :

| ID | Description | Sévérité |
|----|-------------|----------|
| [[tech-debt-registry#TD-2026-016]] | `integrity-check.sh` à migrer Python | 🟠 Haute |
| [[tech-debt-registry#TD-2026-017]] | `nightly-agent.sh` masque échec rsync critique | 🟡 Moyenne |
| [[tech-debt-registry#TD-2026-018]] | `nightly-agent.sh` trap EXIT ne couvre pas SIGKILL | 🟡 Moyenne |

---

## Alternatives écartées

### Alt 1 — Tout migrer en Python
**Rejet** : imposerait un `subprocess` wrapper pour appeler le CLI `claude`, `rsync`, `launchctl`. Zéro gain en clarté pour 3× plus de code. Pas de portabilité Linux gagnée (launchd est macOS-only de toute façon).

### Alt 2 — Tout migrer en bash
**Rejet** : impossible de faire tourner Anthropic Batch API, MCP stdio JSON-RPC, ou scoring arXiv en shell. Les 1860 lignes de logique métier actuelles seraient illisibles en bash.

### Alt 3 — Rust / Go pour les scripts bash
**Rejet hors scope** : complexité déploiement sur macOS + iCloud + launchd pour un dev seul. ROI négatif.

---

## Validation future

Cette ADR doit être révisée si :
- Un script bash dépasse 80 lignes
- Un nouveau parsing de format structuré apparaît en shell
- Un besoin de portabilité Linux apparaît pour un script bash
- Le projet acquiert plusieurs contributeurs (revoir tests)

---

## Liens
- [[audit-setup-claude-code-2026-04-13]] — audit source
- [[tech-debt-registry]] — dette technique
- [[discovery-nightly-agent-architecture]]
- [[decision-architecture-hybride-second-brain]]

## Tags
#decision #architecture #ADR #bash #python #boundary
