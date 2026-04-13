# Vault-as-Graph-Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Réduire le boot cost de la session Claude Code de 14% à ~0.25% en migrant les memory files vers une architecture "Vault-as-Graph-Memory" (MOCs + Memory Tool natif + claude-mem search-only + retrieval 2-tiers LLM-as-retriever/embeddings).

**Architecture:** Le vault Obsidian devient la source unique de vérité, consulté via graph traversal depuis MOCs auto-générés. Memory Tool natif ne garde que 2 fichiers ultra-minimaux (user_profile + session_pointer). Claude-mem reste indexé (Chroma) mais n'injecte plus au boot — accessible uniquement via MCP search.

**Tech Stack:** Bash + Python (test integrity), YAML frontmatter, Obsidian wikilinks, claude-mem MCP, Anthropic Memory Tool (`memory_20250818`).

**Spec source:** [`docs/superpowers/specs/2026-04-13-vault-as-graph-memory-design.md`](../specs/2026-04-13-vault-as-graph-memory-design.md)

---

## File Structure

### Fichiers à CRÉER

| Path | Responsabilité |
|------|----------------|
| `_meta/moc/moc-index.md` | Master MOC — table des autres MOCs avec scope |
| `projects/second-brain/architecture-paper-synthesizer.md` | Note vault manquante (gap memory) |
| `.claude/commands/load-moc.md` | Skill `/load-moc <topic>` retrieval 2-tiers |
| `~/.claude/<memory-tool-path>/user_profile.md` | Memory Tool natif — profil user (OQ1) |
| `~/.claude/<memory-tool-path>/session_pointer.md` | Memory Tool natif — pointer session |
| `tests/test_moc_index.py` | Tests pour validation moc-index.md generation |

### Fichiers à MODIFIER

| Path | Changement |
|------|-----------|
| `_meta/moc/moc-*.md` (8 existants) | Ajouter frontmatter YAML |
| `.nightly-prompt.md` | Règles génération moc-index + frontmatter + cap 30 notes |
| `~/.claude-mem/settings.json` | `CONTEXT_OBSERVATIONS=0`, `SHOW_LAST_SUMMARY=false` |
| `~/.claude/projects/<path>/memory/MEMORY.md` | Réécrire en 3 lignes pointer |
| `integrity_check.py` | Alerter sur conflits iCloud dans `_meta/` |

### Fichiers à SUPPRIMER (après backup)

| Path | Raison |
|------|--------|
| `_meta/moc/moc-X 2.md` (6 fichiers) | iCloud conflicts |
| `~/.claude/projects/<path>/memory/project_*.md` (7 fichiers) | Contenu dupliqué dans vault |

---

## Préambule — Setup branche + backup

### Task 0: Préparation environnement

**Files:** Aucun (opérations git)

- [ ] **Step 1: Créer branche dédiée pour l'implémentation**

```bash
cd /Users/djemildavid/Documents/Obsidian/KnowledgeBase
git checkout sprint2/track-b-notebooklm
git pull --rebase origin sprint2/track-b-notebooklm 2>/dev/null || true
git checkout -b refactor/vault-as-graph-memory
```

- [ ] **Step 2: Backup préventif de ~/.claude/projects/.../memory/**

```bash
MEMORY_DIR="$HOME/.claude/projects/-Users-djemildavid-Documents-Obsidian-KnowledgeBase/memory"
BACKUP_FILE="/tmp/memory-backup-$(date -u +%Y-%m-%dT%H%M%SZ).tar.gz"
tar czf "$BACKUP_FILE" -C "$MEMORY_DIR" .
echo "Backup: $BACKUP_FILE"
ls -la "$BACKUP_FILE"
```

Expected output: fichier `.tar.gz` d'environ 5-10 KB.

- [ ] **Step 3: Vérifier état git propre avant migration**

```bash
git status --short | head -10
```

Expected: liste des modifications pré-existantes (logs, meta), branche `refactor/vault-as-graph-memory`.

---

## Phase 1 — Nettoyage vault (iCloud conflicts + note manquante)

### Task 1: Supprimer les 6 fichiers iCloud conflicts dans `_meta/moc/`

**Files:**
- Delete: `_meta/moc/moc-architecture 2.md`, `moc-decision 2.md`, `moc-discovery 2.md`, `moc-gpparts 2.md`, `moc-second-brain 2.md`, et tout autre "X 2.md"

- [ ] **Step 1: Lister les conflits pour confirmation**

```bash
ls -la _meta/moc/ | grep " 2\."
```

Expected: 6 fichiers listés avec suffixe ` 2.md`.

- [ ] **Step 2: Vérifier qu'ils sont identiques aux originaux (safety check)**

```bash
for f in _meta/moc/*" 2.md"; do
  orig="${f% 2.md}.md"
  if diff -q "$f" "$orig" >/dev/null 2>&1; then
    echo "OK identical: $f"
  else
    echo "⚠️  DIFFERENT: $f vs $orig — INSPECT BEFORE DELETE"
  fi
done
```

Expected: tous "OK identical". Si différent, inspecter avant de continuer.

- [ ] **Step 3: Supprimer les conflits**

```bash
rm _meta/moc/*" 2.md"
ls _meta/moc/
```

Expected: uniquement les 8 MOCs originaux + `.gitkeep`.

- [ ] **Step 4: Commit**

```bash
git add _meta/moc/
git commit -m "chore(moc): remove 6 iCloud conflict duplicates"
```

### Task 2: Créer la note manquante `architecture-paper-synthesizer.md`

**Files:**
- Create: `projects/second-brain/architecture-paper-synthesizer.md`

**Contexte:** Le memory file `project_paper-synthesizer-pipeline.md` contient des infos qui ne sont pas dans le vault (specs Anthropic Batch API, poll interval, Tier filter). Migrer ce contenu en note vault avant suppression du memory file.

- [ ] **Step 1: Créer la note avec contenu migré**

```bash
cat > projects/second-brain/architecture-paper-synthesizer.md <<'EOF'
---
type: architecture
tier: A
created: 2026-04-13
tags: [second-brain, paper-synthesizer, anthropic-batch, pipeline]
domain: second-brain
---

# Paper Synthesizer — Architecture

## Essentiel
`paper_synthesizer.py` produit des **concept extractions atomiques** (Tier S/A/B), pas des digest blobs. C'est une doctrine anti-Collector's-Fallacy : chaque concept extrait est une unité indépendante testable.

## Stack
- **Model**: Claude Haiku via Anthropic Batch API (migré depuis Gemini EU-bloqué, F22)
- **Cache**: `cache_control: ephemeral` pour shared context entre batch items
- **Poll interval**: 60 secondes sur batch status
- **Output**: `_inbox/raw/concepts/{tier}-*.md` pour Tier S/A; digest 1-ligne pour Tier B

## Tier filter
- **Tier S**: concept central du Mind Map + ≥ 2 sous-questions non-triviales → pre-note atomique
- **Tier A**: concept Study Guide avec ≥ 1 sous-question → pre-note atomique
- **Tier B**: mentionné en 1 phrase sans sous-question → 1-liner dans digest

## Liens
- [[decision-weekly-extractor-approach-c]] — approche C validée
- [[feature-weekly-extractor-first-run]] — premier run 45 concepts
- [[decision-architecture-hybride-second-brain]] — architecture globale

<!-- Migré depuis memory/project_paper-synthesizer-pipeline.md (2026-04-13) -->
EOF
```

- [ ] **Step 2: Vérifier la note**

```bash
cat projects/second-brain/architecture-paper-synthesizer.md | head -20
wc -l projects/second-brain/architecture-paper-synthesizer.md
```

Expected: ~30 lignes, frontmatter YAML correct.

- [ ] **Step 3: Commit**

```bash
git add projects/second-brain/architecture-paper-synthesizer.md
git commit -m "docs(vault): migrate paper-synthesizer architecture from memory to vault"
```

---

## Phase 2 — MOCs enhanced (frontmatter YAML + moc-index)

### Task 3: Créer `moc-index.md` master

**Files:**
- Create: `_meta/moc/moc-index.md`

- [ ] **Step 1: Créer le MOC master**

```bash
cat > _meta/moc/moc-index.md <<'EOF'
---
type: moc
scope: "Master index of all MOCs — routing table for /load-moc skill"
notes_count: 0
last_updated: 2026-04-13
generated_by: manual (will be overridden by nightly)
---

# MOC — Master Index

> **Routing table** pour `/load-moc <topic>` — charge le MOC approprié selon le scope.

## MOCs thématiques

| MOC | Scope | Notes | Quand l'utiliser |
|-----|-------|-------|------------------|
| [[moc-second-brain]] | Principal cross-domain | 27 | Entry point principal — si doute |
| [[moc-architecture]] | Décisions architecture, patterns, pipeline | 12 | Questions "comment c'est conçu / pourquoi ce choix" |
| [[moc-decision]] | ADRs uniquement | — | Rappel d'une décision passée précise |
| [[moc-discovery]] | Findings / learnings | — | "Qu'est-ce qu'on a appris sur X ?" |
| [[moc-anti-bug]] | Bugs résolus + patterns d'évitement | — | Debug, prévention régression |
| [[moc-nightly-agent]] | Pipeline nocturne (launchd, corpus, synth) | 5 | Questions sur cron, nightly-agent.sh |
| [[moc-security]] | Sécurité, secrets, permissions, audits | — | Audit sécurité, gestion keychain |
| [[moc-gpparts]] | Projet annexe GPParts | — | Si projet GPParts (pas Second Brain) |

## Règles de routing

1. **Exact match** : si `<topic>` contient un tag de la colonne Scope → charger ce MOC direct
2. **Multi-MOC** : si topic croise 2 scopes (ex: "crash nightly" = anti-bug + nightly-agent) → charger les 2
3. **Ambigu** : si pas de match clair → charger `moc-second-brain.md` (master cross-domain)
4. **Hors-vault** : si la query est sur de l'historique de sessions → invoke `mcp__claude-mem__search` à la place

## Auto-generation

Ce fichier est **régénéré chaque nuit** par `.nightly-prompt.md` après mise à jour des MOCs.
Modifications manuelles de la section "MOCs thématiques" seront écrasées.

## Tags
#meta #moc #routing
EOF
```

- [ ] **Step 2: Vérifier format**

```bash
head -15 _meta/moc/moc-index.md
wc -l _meta/moc/moc-index.md
```

Expected: ~40 lignes, frontmatter YAML valide.

- [ ] **Step 3: Commit**

```bash
git add _meta/moc/moc-index.md
git commit -m "feat(moc): add master moc-index.md for /load-moc routing"
```

### Task 4: Ajouter frontmatter YAML aux 8 MOCs existants

**Files:**
- Modify: `_meta/moc/moc-{second-brain,architecture,decision,discovery,anti-bug,nightly-agent,security,gpparts}.md`

**Approche:** Script shell pour ajouter un frontmatter YAML standard à chaque MOC. Le contenu existant (titre + liste) est préservé.

- [ ] **Step 1: Créer script d'ajout frontmatter**

```bash
cat > /tmp/add-moc-frontmatter.sh <<'EOF'
#!/bin/bash
set -euo pipefail

for f in _meta/moc/moc-*.md; do
  name=$(basename "$f" .md)
  # Skip moc-index (déjà frontmatter)
  [ "$name" = "moc-index" ] && continue

  tag="${name#moc-}"
  # Skip si frontmatter déjà présent
  if head -1 "$f" | grep -q "^---$"; then
    echo "SKIP (already has frontmatter): $f"
    continue
  fi

  # Count notes (lines matching [[...]] pattern)
  notes_count=$(grep -c "^\- \[\[" "$f" || echo 0)

  # Build new file with frontmatter
  tmp=$(mktemp)
  cat > "$tmp" <<FM
---
type: moc
tag: $tag
notes_count: $notes_count
last_updated: $(date +%Y-%m-%d)
scope: "auto-generated MOC for tag #$tag"
---
FM
  cat "$f" >> "$tmp"
  mv "$tmp" "$f"
  echo "OK: $f (notes_count=$notes_count)"
done
EOF
chmod +x /tmp/add-moc-frontmatter.sh
```

- [ ] **Step 2: Exécuter le script**

```bash
/tmp/add-moc-frontmatter.sh
```

Expected output : 8 lignes "OK: _meta/moc/moc-X.md (notes_count=N)".

- [ ] **Step 3: Vérifier frontmatter sur chaque MOC**

```bash
for f in _meta/moc/moc-*.md; do
  echo "=== $f ==="
  head -8 "$f"
  echo ""
done
```

Expected: chaque fichier (sauf moc-index qui a déjà son frontmatter) commence par `---\ntype: moc\ntag: ...\n---`.

- [ ] **Step 4: Valider YAML parseable**

```bash
for f in _meta/moc/moc-*.md; do
  python3 -c "
import sys, yaml
content = open('$f').read()
if content.startswith('---'):
    parts = content.split('---', 2)
    if len(parts) >= 3:
        try:
            yaml.safe_load(parts[1])
            print(f'✅ $f')
        except yaml.YAMLError as e:
            print(f'❌ $f: {e}')
            sys.exit(1)
    else:
        print(f'❌ $f: frontmatter non fermé')
        sys.exit(1)
"
done
```

Expected: 9 lignes "✅".

- [ ] **Step 5: Commit**

```bash
git add _meta/moc/
git commit -m "feat(moc): add YAML frontmatter (type/tag/notes_count/scope) to 8 existing MOCs"
```

### Task 5: Mettre à jour `.nightly-prompt.md` pour les règles MOC

**Files:**
- Modify: `.nightly-prompt.md` (section tag → MOC generation)

- [ ] **Step 1: Lire la section actuelle MOC**

```bash
grep -n "moc/moc-{tag}" .nightly-prompt.md
sed -n '420,440p' .nightly-prompt.md
```

Expected: section à partir de ligne ~425 contenant "Pour chaque tag apparaissant dans 5 notes ou plus".

- [ ] **Step 2: Identifier le bloc exact à remplacer**

Rechercher le bloc complet de génération MOC pour le remplacer par version enrichie avec frontmatter + cap 30 + moc-index.

```bash
awk '/moc-{tag}\.md/,/^###|^##/' .nightly-prompt.md | head -30
```

- [ ] **Step 3: Remplacer la règle par version enrichie**

Ouvrir `.nightly-prompt.md` et remplacer la section moc-generation par :

```markdown
### Génération / mise à jour des MOCs

Pour chaque tag apparaissant dans **5 notes ou plus** → générer ou mettre à jour `_meta/moc/moc-{tag}.md` avec ce format exact :

```markdown
---
type: moc
tag: {tag}
notes_count: {N}
last_updated: YYYY-MM-DD
scope: "auto-generated MOC for tag #{tag}"
---
# MOC — #{tag}
Generated: YYYY-MM-DD | {N} notes

- [[note-name]] — description dense 1 ligne
...
```

**Règles supplémentaires :**
1. Format de chaque note : `- [[note-name]] — {summary_dense_1_ligne}` (max 120 chars après le `—`)
2. Si `notes_count > 30` → proposer un split thématique (ex: `moc-architecture-decisions`, `moc-architecture-patterns`) dans une note de maintenance `_logs/moc-split-suggestions.md`
3. Après génération de tous les MOCs individuels → régénérer `_meta/moc/moc-index.md` avec :
   - Un tableau routing listant chaque MOC avec scope + notes_count
   - Frontmatter `type: moc`, `scope: "Master index..."`, `last_updated`
4. Protéger `_meta/moc/` de toute modification sauf via nightly (ne pas toucher si tests intégrité détectent conflits iCloud — alert uniquement)
```

- [ ] **Step 4: Vérifier l'édition**

```bash
grep -A 20 "Génération / mise à jour des MOCs" .nightly-prompt.md | head -30
```

- [ ] **Step 5: Commit**

```bash
git add .nightly-prompt.md
git commit -m "feat(nightly-prompt): MOC generation rules — frontmatter YAML + moc-index + cap 30"
```

### Task 6: Alerte integrity_check.py sur conflits iCloud dans `_meta/`

**Files:**
- Modify: `integrity_check.py:148-170` (fonction `detect_icloud_conflicts`)
- Modify: `tests/test_integrity_check.py` (nouveau test)

**Note:** Cette task étend le scope fait dans PR #1 pour protéger spécifiquement `_meta/` (critique pour MOCs).

- [ ] **Step 1: Écrire le test failing**

Ajouter à `tests/test_integrity_check.py` dans la classe `TestDetectIcloudConflicts` :

```python
    def test_alerts_on_meta_dir_conflicts(self, tmp_vault):
        # Conflits dans _meta/ doivent être détectés en priorité (MOCs critiques)
        _write_note(tmp_vault / "_meta" / "moc" / "moc-X (Mac mini conflicted copy 2026-04-12).md", "Conflict")
        result = detect_icloud_conflicts(tmp_vault)
        assert len(result) == 1
        assert "_meta/moc" in str(result[0])
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_integrity_check.py::TestDetectIcloudConflicts::test_alerts_on_meta_dir_conflicts -v
```

Expected: FAIL car `_meta/` n'est pas dans `scan_roots` de `detect_icloud_conflicts`.

- [ ] **Step 3: Fixer `detect_icloud_conflicts` pour inclure `_meta/`**

Modifier `integrity_check.py:148-170`. Le fix PR#1 a déjà ajouté `_meta` et `_inbox` dans scan_roots. Vérifier que c'est bien le cas :

```bash
grep -A 3 "scan_roots = " integrity_check.py
```

Expected: `scan_roots = list(ACTIVE_ROOTS) + ["_meta", "_inbox"]`

Si ce n'est pas le cas, le patch PR #1 est le fix. Sinon, le test devrait déjà passer — ce qui confirme que la Task 6 est déjà couverte.

- [ ] **Step 4: Run test to verify it passes**

```bash
python3 -m pytest tests/test_integrity_check.py::TestDetectIcloudConflicts -v
```

Expected: PASS sur tous les tests de la classe.

- [ ] **Step 5: Commit (si changement)**

```bash
# Si tests passent déjà grâce à PR#1, skip commit (pas de modif nécessaire)
# Sinon:
git add integrity_check.py tests/test_integrity_check.py
git commit -m "test(integrity): alert on iCloud conflicts in _meta/ directory"
```

---

## Phase 3 — Skill `/load-moc`

### Task 7: Créer le skill `.claude/commands/load-moc.md`

**Files:**
- Create: `.claude/commands/load-moc.md`

- [ ] **Step 1: Créer le fichier skill**

```bash
cat > .claude/commands/load-moc.md <<'EOF'
---
description: Charge le MOC pertinent pour un topic — retrieval 2-tiers (LLM-routing puis embeddings fallback) ~350 tokens moyen
allowed-tools: Bash(cat:*), Bash(grep:*), Bash(head:*), Bash(ls:*), Bash(wc:*)
argument-hint: "<topic> — ex: 'bash vs python', 'crash nightly', 'security audit'"
---

# /load-moc — Charge MOC pertinent (retrieval 2-tiers)

**Objectif token-efficient** : ~330 tokens moyen par retrieval via graph traversal depuis MOCs.

## Règles absolues

1. **NE PAS** lire tous les MOCs au hasard — toujours passer par `moc-index.md` d'abord
2. **NE PAS** lire de notes individuelles tant que Tier 1 n'a pas sélectionné un MOC
3. **NE PAS** dump de contenu — sortie = citations wikilinks précises

## Tier 1 — LLM-as-retriever (80-90% cas, ~330 tokens)

```bash
cd /Users/djemildavid/Documents/Obsidian/KnowledgeBase

# 1. Read moc-index (le routeur)
echo "=== MOC INDEX ==="
cat _meta/moc/moc-index.md

# 2. Afficher le topic demandé
echo ""
echo "=== TOPIC: $ARGUMENTS ==="
```

**Raisonnement Claude après Tier 1** :
- Parse le tableau routing de `moc-index.md`
- Match `$ARGUMENTS` vs les scopes listés
- Si 1-2 MOCs clairement pertinents → `cat _meta/moc/moc-{tag}.md` directement
- Si ambigu → passer à Tier 2

**Format sortie attendu Tier 1** :
```markdown
## 🎯 MOCs sélectionnés via routing
- `moc-{tag1}.md` — raison du match
- `moc-{tag2}.md` — raison du match (optionnel)

## 📚 Notes pertinentes (suivre les wikilinks)
- [[note-X]] — description from MOC
- [[note-Y]] — description from MOC
```

## Tier 2 — Embeddings fallback (10-20% cas, ~600 tokens)

**Déclenché UNIQUEMENT si Tier 1 retourne "aucun MOC pertinent" ou ambigu.**

Invoquer `mcp__claude-mem__search` avec le topic :

```
mcp__plugin_claude-mem_mcp-search__search(query="$ARGUMENTS", limit=5)
```

Puis Claude raffine avec MOCs des notes trouvées si possible.

## Tier 3 — Master fallback (2% cas, ~500 tokens)

Si Tier 1 et Tier 2 échouent :
```bash
cat _meta/moc/moc-second-brain.md
```

Et laisser Claude scanner la liste complète.

## Budget tokens cible

| Cas | Tokens | Fréquence |
|-----|--------|-----------|
| Tier 1 exact match | ~250 | 70% |
| Tier 1 semantic reasoning | ~380 | 20% |
| Tier 2 embedding fallback | ~700 | 8% |
| Tier 3 master scan | ~600 | 2% |

**Moyenne pondérée** : ~340 tokens par invocation.

## Ne JAMAIS

- Lire une note vault sans passer par un MOC d'abord
- Invoquer Tier 2 avant d'avoir essayé Tier 1
- Retourner de la prose — format strict markdown ci-dessus
- Modifier des fichiers (skill 100% read-only)
EOF
```

- [ ] **Step 2: Vérifier le skill**

```bash
wc -l .claude/commands/load-moc.md
head -10 .claude/commands/load-moc.md
```

Expected: ~80 lignes, frontmatter valide.

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/load-moc.md
git commit -m "feat(skill): /load-moc — 2-tier retrieval (LLM-routing + embeddings fallback)"
```

### Task 8: Test manuel des 5 scenarios `/load-moc`

**Files:** Aucun (test manuel via Bash)

**Note:** On teste que les commandes shell que le skill prescrit fonctionnent bien. Test fonctionnel de Claude (raisonnement) sera fait Phase 7.

- [ ] **Step 1: Scenario 1 — Exact tag match "architecture"**

```bash
cd /Users/djemildavid/Documents/Obsidian/KnowledgeBase
# Simuler Tier 1
head -20 _meta/moc/moc-index.md
echo "---"
cat _meta/moc/moc-architecture.md
```

Expected: les 2 sorties combinées < 800 bytes (~250 tokens). MOC architecture liste ~12 notes.

- [ ] **Step 2: Scenario 2 — Multi-MOC "crash nightly"**

```bash
cat _meta/moc/moc-index.md
echo "---"
cat _meta/moc/moc-anti-bug.md
echo "---"
cat _meta/moc/moc-nightly-agent.md
```

Expected: ~1500 bytes (~450 tokens), 2 MOCs chargés.

- [ ] **Step 3: Scenario 3 — Topic inconnu "mémoire verbose"**

```bash
# Simuler Tier 1 échec → fallback Tier 2
cat _meta/moc/moc-index.md
echo "=== Tier 2 fallback (MCP search — à invoquer dans Claude) ==="
echo "mcp__plugin_claude-mem_mcp-search__search(query='mémoire verbose')"
```

Expected: moc-index chargé, puis MCP search invoqué par Claude.

- [ ] **Step 4: Scenario 4 — Master fallback "quelque chose de vague"**

```bash
cat _meta/moc/moc-index.md
echo "---"
cat _meta/moc/moc-second-brain.md
```

Expected: ~1000 bytes (~300 tokens).

- [ ] **Step 5: Scenario 5 — Mesurer taille totale retrieval moyen**

```bash
# Taille totale pour 3 invocations types
total=0
for f in _meta/moc/moc-index.md _meta/moc/moc-architecture.md _meta/moc/moc-anti-bug.md; do
  size=$(wc -c < "$f")
  total=$((total + size))
done
echo "Total bytes 3 MOCs: $total"
echo "Estim. tokens: $((total / 4))"
```

Expected: 1500-2500 bytes total, ~400-600 tokens — conforme au budget.

- [ ] **Step 6: Commit log du test**

```bash
git log --oneline -5
```

No commit needed (tests manuels, pas de changement de code).

---

## Phase 4 — Memory Tool natif (OQ1)

### Task 9: Research API Memory Tool natif (`memory_20250818`)

**Files:** Aucun (investigation)

**OQ1 du spec:** Identifier comment activer le Memory Tool natif d'Anthropic dans Claude Code CLI.

- [ ] **Step 1: Chercher documentation officielle**

```bash
# Vérifier si doc locale existe dans les plugins ou skills superpowers
grep -rln "memory_20250818\|memory.tool" ~/.claude/plugins/ 2>/dev/null | head -5
grep -rln "memory_20250818" /Users/djemildavid/Documents/Obsidian/KnowledgeBase/ 2>/dev/null | head -5
```

- [ ] **Step 2: Si pas trouvé, WebFetch la doc Anthropic**

Utiliser l'outil `WebFetch` sur :
- `https://docs.claude.com/en/docs/agents-and-tools/tool-use/memory-tool` (après vérif URL exacte)
- `https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool`

Questions précises :
1. Comment activer le Memory Tool dans Claude Code CLI ? (settings.json ?)
2. Où sont stockés les fichiers memory (path par défaut) ?
3. Compatibilité avec l'auto-memory existant (`~/.claude/projects/.../memory/MEMORY.md`) ?
4. Beta header requis (`memory-2025-08-18` ?) ?

- [ ] **Step 3: Documenter les findings**

Créer `docs/superpowers/research/memory-tool-native-findings.md` :

```markdown
# Memory Tool natif — Findings

**Date**: 2026-04-13

## Activation dans Claude Code
[résultat recherche]

## Path de stockage
[résultat recherche]

## Compatibilité auto-memory
[résultat recherche]

## Fallback si non-accessible
Si Memory Tool natif n'est pas accessible via Claude Code CLI en 2026-04, fallback :
- Créer `user_profile.md` + `session_pointer.md` directement dans le dossier auto-memory existant
  (`~/.claude/projects/-Users-djemildavid-Documents-Obsidian-KnowledgeBase/memory/`)
- Ils seront chargés via le mécanisme claudeMd auto-load classique
- Taille cible ~200 tokens total (vs 5280 aujourd'hui)
```

- [ ] **Step 4: Commit research**

```bash
git add docs/superpowers/research/memory-tool-native-findings.md
git commit -m "research: Memory Tool natif activation findings (OQ1 resolution)"
```

### Task 10: Créer `user_profile.md` et `session_pointer.md`

**Files:**
- Create: `<memory-path>/user_profile.md` (path selon findings Task 9)
- Create: `<memory-path>/session_pointer.md`

**Path:** Par défaut `~/.claude/projects/-Users-djemildavid-Documents-Obsidian-KnowledgeBase/memory/`. Si Memory Tool natif fournit un autre chemin (findings Task 9), l'utiliser.

- [ ] **Step 1: Définir MEMORY_PATH**

```bash
export MEMORY_PATH="$HOME/.claude/projects/-Users-djemildavid-Documents-Obsidian-KnowledgeBase/memory"
echo "Memory path: $MEMORY_PATH"
ls "$MEMORY_PATH" | head
```

- [ ] **Step 2: Créer `user_profile.md`**

```bash
cat > "$MEMORY_PATH/user_profile.md" <<'EOF'
---
name: user_profile
description: Profil utilisateur — role, stack, préférences workflow. Ultra-minimal. Ne pas dupliquer du contenu vault.
type: user
---

# User Profile

- **Role**: Senior dev solo (macOS Darwin 25.4.0, zsh)
- **Stack**: Python 3.9+, Bash, Obsidian, Claude Code
- **Workflow**: Second Brain pipeline (vault + nightly launchd + NotebookLM MCP)
- **Preferences**:
  - Skills token-efficient (shell-first pre-processing, cf. [[architecture-token-efficient-skills]])
  - Bash/Python boundary: cf. [[decision-bash-vs-python-boundary]]
  - Testing: TDD pytest (voir `tests/`)
- **Security**: secrets en macOS Keychain (`github-pat` service), jamais en clair
- **Entry point retrieval**: `/load-moc <topic>` — traverse graph depuis `_meta/moc/moc-index.md`
EOF
wc -l "$MEMORY_PATH/user_profile.md"
```

Expected: ~15 lignes.

- [ ] **Step 3: Créer `session_pointer.md`**

```bash
cat > "$MEMORY_PATH/session_pointer.md" <<'EOF'
---
name: session_pointer
description: Pointer session minimaliste — branche, commit, goal. Mis à jour par hooks ou skill /pin-goal.
type: project
---

# Session Pointer

- **Branch**: auto-détecté via `git branch --show-current`
- **Last commit**: auto-détecté via `git log -1 --oneline`
- **Goal**: (user-pinned via `/pin-goal "description"` — optionnel)
- **Last `/load-moc`**: (auto-tracked dans `_logs/load-moc.log` — optionnel)

## Retrieve current state

Invoke `/resume-session` skill pour reconstituer le contexte complet (~300 tokens).
EOF
wc -l "$MEMORY_PATH/session_pointer.md"
```

Expected: ~15 lignes.

- [ ] **Step 4: Vérifier taille totale des 2 fichiers**

```bash
cat "$MEMORY_PATH/user_profile.md" "$MEMORY_PATH/session_pointer.md" | wc -c
```

Expected: ~800-1000 bytes (~200-250 tokens) — conforme au budget Memory Tool.

- [ ] **Step 5: Commit (note: fichiers hors repo, ne pas commit)**

Les memory files sont dans `~/.claude/` pas dans le vault repo. Pas de commit. Backup tar:

```bash
tar czf /tmp/new-memory-tool-files-$(date -u +%Y%m%d).tar.gz -C "$MEMORY_PATH" user_profile.md session_pointer.md
ls /tmp/new-memory-tool-files-*.tar.gz
```

### Task 11: Réduire `MEMORY.md` à pointer minimal

**Files:**
- Modify: `<memory-path>/MEMORY.md`

- [ ] **Step 1: Backup current MEMORY.md**

```bash
cp "$MEMORY_PATH/MEMORY.md" /tmp/MEMORY.md.backup.$(date -u +%Y%m%d)
cat /tmp/MEMORY.md.backup.*
```

- [ ] **Step 2: Réécrire en pointer minimal**

```bash
cat > "$MEMORY_PATH/MEMORY.md" <<'EOF'
# Memory Index — Vault-as-Graph-Memory

Migrated 2026-04-13 — see `docs/superpowers/specs/2026-04-13-vault-as-graph-memory-design.md`.

## Active memory files

- [user_profile.md](user_profile.md) — role, stack, preferences
- [session_pointer.md](session_pointer.md) — branche, goal actuel

## Retrieval

For everything else: invoke `/load-moc <topic>` (graph traversal via `_meta/moc/`)
or `mcp__plugin_claude-mem_mcp-search__search` for historical queries.
EOF
wc -l "$MEMORY_PATH/MEMORY.md"
```

Expected: ~15 lignes (vs 15 avant mais contenu totalement différent).

- [ ] **Step 3: Vérifier**

```bash
cat "$MEMORY_PATH/MEMORY.md"
```

---

## Phase 5 — Claude-mem reconfiguration

### Task 12: Désactiver injection claude-mem au boot

**Files:**
- Modify: `~/.claude-mem/settings.json`

- [ ] **Step 1: Backup settings.json claude-mem**

```bash
cp ~/.claude-mem/settings.json /tmp/claude-mem-settings.backup.$(date -u +%Y%m%d).json
cat ~/.claude-mem/settings.json | python3 -m json.tool | head -50
```

- [ ] **Step 2: Modifier les 2 clés clés via Python (atomic)**

```bash
python3 <<'EOF'
import json, os
path = os.path.expanduser("~/.claude-mem/settings.json")
with open(path) as f:
    data = json.load(f)

# Désactiver injection boot (voir spec section 3.6)
data["CLAUDE_MEM_CONTEXT_OBSERVATIONS"] = 0
data["CLAUDE_MEM_SHOW_LAST_SUMMARY"] = False
# Garder Chroma enabled pour MCP search (Tier 2 fallback)
data["CLAUDE_MEM_CHROMA_ENABLED"] = True
# Garder SEMANTIC_INJECT=false (pas d'injection boot même via embeddings)
data["CLAUDE_MEM_SEMANTIC_INJECT"] = False

# Atomic write
tmp = path + ".tmp"
with open(tmp, "w") as f:
    json.dump(data, f, indent=2)
os.replace(tmp, path)
print("✅ Settings mis à jour")
EOF
```

- [ ] **Step 3: Vérifier les clés**

```bash
python3 -c "
import json, os
with open(os.path.expanduser('~/.claude-mem/settings.json')) as f:
    d = json.load(f)
print('CONTEXT_OBSERVATIONS:', d.get('CLAUDE_MEM_CONTEXT_OBSERVATIONS'))
print('SHOW_LAST_SUMMARY:', d.get('CLAUDE_MEM_SHOW_LAST_SUMMARY'))
print('CHROMA_ENABLED:', d.get('CLAUDE_MEM_CHROMA_ENABLED'))
print('SEMANTIC_INJECT:', d.get('CLAUDE_MEM_SEMANTIC_INJECT'))
"
```

Expected output:
```
CONTEXT_OBSERVATIONS: 0
SHOW_LAST_SUMMARY: False
CHROMA_ENABLED: True
SEMANTIC_INJECT: False
```

### Task 13: Vérifier que `mcp__claude-mem__search` reste accessible

**Files:** Aucun (test)

- [ ] **Step 1: Vérifier que le MCP server claude-mem tourne**

```bash
curl -sf http://localhost:37777/health 2>&1 | head
# Si vide, le worker tourne mais n'expose pas /health au public; normal
```

- [ ] **Step 2: Vérifier config MCP dans enabledMcpjsonServers**

```bash
grep -A 5 "enabledMcpjsonServers" .claude/settings.local.json | head -10
```

Expected: `github` listé. `claude-mem` est enabled au niveau plugin, pas via .mcp.json du projet — OK.

- [ ] **Step 3: Lister les tools MCP claude-mem disponibles**

```bash
ls ~/.claude/plugins/cache/thedotmack/claude-mem/12.1.0/scripts/mcp-server.cjs 2>/dev/null
```

Expected: fichier existe. Les tools seront disponibles au prochain boot de session.

---

## Phase 6 — Big bang migration

### Task 14: Supprimer les 7 memory files legacy

**Files:**
- Delete: `<memory-path>/project_*.md` (7 fichiers)

- [ ] **Step 1: Re-lister les fichiers à supprimer**

```bash
ls "$MEMORY_PATH"/project_*.md
```

Expected: 7 fichiers (audit, bash-rules, future-managed-agents, paper-synthesizer, architecture-v5, session-state, skills-custom).

- [ ] **Step 2: Vérifier backup existe**

```bash
ls -la /tmp/memory-backup-*.tar.gz | tail -1
```

Expected: archive existe (créée en Task 0 Step 2).

- [ ] **Step 3: Supprimer les 7 fichiers**

```bash
rm "$MEMORY_PATH"/project_audit-2026-04-13.md
rm "$MEMORY_PATH"/project_bash-vs-python-rules.md
rm "$MEMORY_PATH"/project_future-managed-agents.md
rm "$MEMORY_PATH"/project_paper-synthesizer-pipeline.md
rm "$MEMORY_PATH"/project_second-brain-architecture-v5.md
rm "$MEMORY_PATH"/project_session-state-2026-04-12.md
rm "$MEMORY_PATH"/project_skills-custom.md
```

- [ ] **Step 4: Vérifier état final du dossier memory**

```bash
ls -la "$MEMORY_PATH"
```

Expected:
- MEMORY.md (minimal)
- user_profile.md
- session_pointer.md
(ces 3 fichiers seulement)

- [ ] **Step 5: Calculer taille totale memory**

```bash
wc -c "$MEMORY_PATH"/*.md
echo "Total tokens estim: $((  $(cat "$MEMORY_PATH"/*.md | wc -c) / 4 ))"
```

Expected: ~1500 bytes, ~370 tokens (vs 18474 bytes / 5280 tokens avant = -92%).

### Task 15: Redémarrer Claude Code et mesurer boot cost

**Files:** Aucun (test empirique)

- [ ] **Step 1: Capturer état actuel avant restart**

```bash
echo "=== État pré-restart ==="
echo "Memory path content:"
ls "$MEMORY_PATH"
echo ""
echo "claude-mem config:"
python3 -c "import json, os; print(json.dumps({k:v for k,v in json.load(open(os.path.expanduser('~/.claude-mem/settings.json'))).items() if 'CLAUDE_MEM_CONTEXT' in k or 'CHROMA' in k or 'SEMANTIC' in k or 'SUMMARY' in k}, indent=2))"
```

- [ ] **Step 2: Documenter l'instruction pour l'utilisateur**

Plan d'action manuel pour l'utilisateur :
```
1. Fermer la session Claude Code courante
2. Ouvrir une nouvelle session Claude Code (nouvelle fenêtre ou /clear)
3. Premier prompt: "montre-moi les tokens consommés au boot"
4. Observer le %age (devrait être < 1% vs 14% avant)
```

Alternative automatisée : si l'implémentation est faite par un subagent, l'user doit valider à la fin.

- [ ] **Step 3: Enregistrer la mesure post-restart (une fois faite)**

Créer `_logs/memory-migration-metrics-2026-04-13.md` avec les résultats.

---

## Phase 7 — Validation finale

### Task 16: Exécuter les 5 scenarios de validation

**Files:**
- Create: `_logs/memory-migration-metrics-2026-04-13.md` (log résultats)

**Note:** Cette task nécessite une session Claude Code fraîche (post-restart de Task 15). Les scenarios sont des prompts à faire à Claude et dont on note la taille de réponse.

- [ ] **Step 1: Créer le fichier de résultats**

```bash
cat > _logs/memory-migration-metrics-2026-04-13.md <<'EOF'
# Memory Migration — Validation Metrics (2026-04-13)

## Baseline (avant migration)

- Boot cost: 28 000 tokens (14% de 200K)
- Memory files: 8 fichiers, ~5 280 tokens chargés
- Timeline priming claude-mem: ~11 800 tokens

## Post-migration (à remplir après Task 15)

- Boot cost: TBD tokens (TBD % de 200K)
- Memory files: 3 fichiers (MEMORY.md minimal + user_profile + session_pointer)
- Timeline priming: 0 (désactivé)

## Target vs Acceptable

| Métrique | Cible | Acceptable | Mesuré |
|----------|-------|------------|--------|
| Boot cost (tokens) | 500 | < 2000 | TBD |
| Boot cost (%) | 0.25% | < 1% | TBD |

## 5 scenarios de validation

### Scenario 1: Query simple (pointer direct)
**Prompt**: "Quelles sont les règles bash vs python du projet ?"
**Attente**: Claude utilise le pointer [[decision-bash-vs-python-boundary]] depuis user_profile.md, Read direct la note.
**Tokens consommés**: TBD
**Statut**: TBD

### Scenario 2: Query topic connu (via MOC)
**Prompt**: "Invoke /load-moc architecture et synthétise les décisions clés"
**Attente**: Tier 1 route vers `moc-architecture`, Claude charge et synthétise.
**Tokens**: TBD
**Statut**: TBD

### Scenario 3: Query topic inconnu (fallback Chroma)
**Prompt**: "Invoke /load-moc 'pattern verbose reduction'"
**Attente**: Tier 1 miss → Tier 2 mcp__claude-mem__search.
**Tokens**: TBD
**Statut**: TBD

### Scenario 4: Query historique
**Prompt**: "Qu'est-ce qu'on a fait dans la session d'hier ?"
**Attente**: Claude invoke `mcp__claude-mem__timeline`.
**Tokens**: TBD
**Statut**: TBD

### Scenario 5: /resume-session
**Prompt**: "/resume-session"
**Attente**: Skill tourne, output ~300 tokens, contexte reconstitué.
**Tokens**: TBD
**Statut**: TBD

## Conclusions

TBD après exécution.

## Rollback si besoin

```bash
# Restaurer les 7 memory files legacy
tar xzf /tmp/memory-backup-2026-04-13T*.tar.gz -C "$HOME/.claude/projects/-Users-djemildavid-Documents-Obsidian-KnowledgeBase/memory/"
# Restaurer settings claude-mem
cp /tmp/claude-mem-settings.backup.2026*.json ~/.claude-mem/settings.json
# Redémarrer Claude Code
```
EOF
```

- [ ] **Step 2: Commit le template de résultats**

```bash
git add _logs/memory-migration-metrics-2026-04-13.md
git commit -m "docs: memory migration validation template — scenarios to fill post-restart"
```

- [ ] **Step 3: (Après session restart manuel) remplir les scenarios**

L'utilisateur ou subagent post-restart doit :
1. Lancer chacun des 5 prompts dans une session fraîche
2. Noter les tokens mesurés dans le fichier
3. Mettre `✅/⚠️/❌` sur chaque scenario
4. Commit le fichier rempli

```bash
# Après remplissage:
git add _logs/memory-migration-metrics-2026-04-13.md
git commit -m "docs: memory migration validation results — boot cost measured"
```

### Task 17: Créer PR pour la migration

**Files:** Aucun (opérations git/gh)

- [ ] **Step 1: Push branche**

```bash
git push -u origin refactor/vault-as-graph-memory
```

- [ ] **Step 2: Créer PR vers sprint2 (même base que les 2 autres PRs)**

```bash
gh pr create --base sprint2/track-b-notebooklm \
  --title "refactor(memory): Vault-as-Graph-Memory architecture (-97% boot cost)" \
  --body "$(cat <<'BODY'
## Summary

Migration majeure de l'architecture de mémoire persistante cross-session.

**Avant** : 14% de boot cost (28K tokens) dû au timeline priming claude-mem + 8 memory files dupliquant 48% du vault.
**Après** : ~0.25% boot cost (~500 tokens) via Vault-as-Graph-Memory.

## Architecture — 5 couches

- Couche 0: Memory Tool natif (user_profile + session_pointer, ~200 tok)
- Couche 1: Skills metadata progressive disclosure (~300 tok)
- Couche 2: Vault MOCs (lazy, via /load-moc)
- Couche 3: Vault notes (lazy via wikilinks)
- Couche 4: claude-mem search-only (MCP, plus d'injection boot)

## Changements clés

- ✅ 8 MOCs enrichis avec frontmatter YAML
- ✅ moc-index.md master pour routing
- ✅ Skill `/load-moc` retrieval 2-tiers (LLM + Chroma fallback)
- ✅ user_profile.md + session_pointer.md minimaux
- ✅ claude-mem reconfiguré (CONTEXT_OBSERVATIONS=0)
- ✅ 7 memory files legacy supprimés (contenu déjà dans vault)
- ✅ .nightly-prompt.md mis à jour pour générer moc-index

## Targets mesurés

Voir `_logs/memory-migration-metrics-2026-04-13.md` pour résultats complets.

## Rollback

Backup tar.gz dans `/tmp/memory-backup-*.tar.gz`. Settings claude-mem également backupés. Rollback en 2 commandes (voir doc).

## Spec source

`docs/superpowers/specs/2026-04-13-vault-as-graph-memory-design.md`

🤖 Generated with [Claude Code](https://claude.com/claude-code)
BODY
)" 2>&1 | tail -3
```

---

## Self-Review Checklist

Après écriture complète du plan, je vérifie :

**1. Spec coverage:**
- ✅ Section 3.1 (5 couches) → Tasks 3, 4, 7, 10, 11, 12
- ✅ Section 3.2 (user_profile) → Task 10
- ✅ Section 3.3 (skills) → Task 7
- ✅ Section 3.4 (MOCs) → Tasks 3, 4, 5
- ✅ Section 3.5 (notes) → Pas de modif requise
- ✅ Section 3.6 (claude-mem) → Task 12
- ✅ Section 5 (migration 7 phases) → Tasks 0-17
- ✅ Section 6 (métriques) → Tasks 15, 16
- ✅ Section 7 (risks) → backups (Task 0), rollback docs (Task 16), integrity alert (Task 6)
- ✅ OQ1 (Memory Tool API) → Task 9
- ✅ OQ2 (session_pointer update) → Task 10 (template avec skill-driven)
- ✅ OQ3 (MOC cap 30) → Task 5

**2. Placeholder scan:**
- Memory path `<memory-path>` dans Task 10/11 → exporté via `$MEMORY_PATH` en Step 1
- "TBD" dans Task 16 scenarios → explicit placeholder for post-restart fill-in, legitimate
- Pas de "TODO" ou "à définir" ailleurs

**3. Type consistency:**
- `MEMORY_PATH` utilisé de manière cohérente Tasks 10, 11, 14
- `moc-index.md` référencé de manière consistante Tasks 3, 5, 7, 9
- `CLAUDE_MEM_CONTEXT_OBSERVATIONS` same name across spec + Task 12

Plan OK — prêt à exécuter.

---

## Execution options

Après review du plan par user :

**1. Subagent-Driven (recommandé)** — Dispatch fresh subagent per task, review between tasks
**2. Inline Execution** — Execute in this session avec checkpoints

Tasks indépendantes (peuvent paralléliser) :
- Task 1 + Task 2 (cleanup vault)
- Task 3 + Task 4 (MOCs — mais Task 4 dépend de Task 1 complete)
- Task 7 + Task 10 (skill + memory tool)

Tasks séquentielles strictes :
- Task 14 dépend de Task 11 (memory tool files créés)
- Task 15 dépend de Task 14 (suppression terminée)
- Task 16 dépend de Task 15 (restart fait)
