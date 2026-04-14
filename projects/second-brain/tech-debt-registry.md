---
status: active
priority: high
created: 2026-04-13
updated: 2026-04-13
tags: [tech-debt, registry, tracking]
domain: second-brain
type: registry
---

# Tech Debt Registry — Second Brain Pipeline

> Registre vivant de la dette technique. Mis à jour à chaque audit ou découverte.
> Format : `TD-<année>-<num>` | sévérité | statut | description | action

---

## 🚨 Critiques (à traiter immédiatement)

### TD-2026-001 — GitHub PAT exposé en clair dans settings ✅
**Sévérité** : 🔴 CRITIQUE (fuite secret)
**Découvert** : 2026-04-13 (audit Opus)
**Statut** : `resolved` (2026-04-13 ~10h00)
**Fichier** : `~/.claude/settings.json` lignes 3-4 (retirées)
**Détail** : Token `ghp_REDACTED_xxxxxxxxxxxxxxxxxxxx` en dur, dupliqué sur `GITHUB_TOKEN` + `GITHUB_PERSONAL_ACCESS_TOKEN`.
**Actions réalisées** :
1. ✅ Token révoqué sur github.com/settings/tokens
2. ✅ Nouveau PAT généré avec scopes Large (repo/workflow/admin:public_key/gist/write:packages)
3. ✅ Stocké dans macOS Keychain (`security add-generic-password -U -a djemildavid -s github-pat`)
4. ✅ `~/.zshrc` configuré pour charger depuis Keychain au démarrage shell
5. ✅ Lignes `env.GITHUB_*` retirées de `~/.claude/settings.json`
6. ✅ Backups `~/.claude/backups/` vérifiés — ne contenaient PAS l'ancien PAT (ce sont des backups de user prefs, pas settings)
**Traces historiques** : option A retenue — laissées telles quelles dans `~/.claude/file-history/` et JSONL claude-mem. Secrets révoqués = inoffensifs.
**Commande de récupération** : `security find-generic-password -a djemildavid -s github-pat -w`

### TD-2026-002 — 2 Google API Keys exposées dans settings projet ✅
**Sévérité** : 🔴 CRITIQUE (fuite secret)
**Découvert** : 2026-04-13 (audit Opus)
**Statut** : `resolved` (2026-04-13 ~10h00)
**Fichier** : `.claude/settings.local.json` lignes 47-48 (+ `~/.zshrc` L.84, `~/.zshenv` L.1)
**Détail** : Clés `AIzaSy_REDACTED_oldkey` et `AIzaSy_REDACTED_newkey` embarquées dans pattern `sed` de permissions + `export GOOGLE_API_KEY="AIzaSy…"` dans zshrc/zshenv.
**Actions réalisées** :
1. ✅ Les 2 clés révoquées sur console.cloud.google.com
2. ✅ Historique git audité — aucune trace committée (`git log --all -p -S "AIzaSy"` = vide)
3. ✅ Pas de régénération — user n'utilise plus Google API (Gemini bloqué EU de toute façon)
4. ✅ `~/.zshrc` L.84 retirée
5. ✅ `~/.zshenv` vidé complètement (contenait uniquement le secret)
6. ✅ `.claude/settings.local.json` L.47-48 retirées (pattern sed + export)
7. ✅ 3 lignes additionnelles nettoyées dans settings.local.json (permissions ajoutées pendant audit — fragments de tokens dans patterns grep)
**Traces historiques** : option A retenue — laissées dans logs claude-mem. Secrets révoqués = inoffensifs.

### TD-2026-003 — Permissions settings trop larges ✅
**Sévérité** : 🟠 HAUTE (escalation potentielle)
**Découvert** : 2026-04-13 (audit Opus)
**Statut** : `resolved` (2026-04-13 ~11h20)
**Fichier** : `.claude/settings.local.json`
**Détail** : Globs permissifs (`Read(//Users/djemildavid/**)`, `Bash(python3)`, `Bash(pip3 install:*)`, `Bash(brew install:*)`).
**Actions réalisées** :
1. ✅ Retiré `Bash(python3 -c ':*)` (exécution python inline arbitraire)
2. ✅ Retiré `Bash(pip3 install:*)` (installation paquets sans garde)
3. ✅ Retiré `Bash(brew install:*)` (installation brew sans garde)
4. ✅ Retiré `Read(//opt/homebrew/**)` (wildcard système entier)
5. ✅ Remplacé `Read(//Users/djemildavid/**)` par 3 paths spécifiques (Obsidian + .zshrc + .zshenv)
6. ✅ Remplacé `Read(//Users/djemildavid/.claude/**)` par 4 paths spécifiques (settings, mcp, plugins, memory)
7. ✅ Retiré `/Users/djemildavid` du `additionalDirectories` (gardé : KnowledgeBase + .claude)
**Reste** : Bash(pip3 install) et Bash(brew install) doivent être confirmés à chaque usage maintenant.

---

## ⚠️ Hautes (semaine courante)

### TD-2026-004 — Slash command `/notebooklm-weekly` est un stub vide ❌ FAUX POSITIF
**Sévérité** : 🟠 HAUTE (feature bloquée)
**Découvert** : 2026-04-13 (audit Opus)
**Statut** : `wontfix` (2026-04-13) — **faux positif de l'audit**
**Fichier** : `.claude/commands/notebooklm-weekly.md`
**Détail audit erroné** : "Fichier d'UNE SEULE LIGNE"
**Vérification 2026-04-13 11h** : `wc -l` → **384 lignes**. C'est un skill complet, bien structuré :
- 4 phases (Préparation, Chargement notebook, Extraction ordonnée, Mise à jour état)
- Bibliothèque Q&A ciblée par domaine (universal + ai/cloud/ecommerce/iot)
- Format frontmatter détaillé pour les pre-notes
- Test anti-Collector's Fallacy intégré
- Gestion d'état `_meta/notebooklm-state.json`
**Conclusion** : agent Opus de l'audit s'est trompé. Aucune action requise.
**Leçon** : pour les audits futurs, croiser les findings avec un `wc -l` ou Read direct.

### TD-2026-005 — MCP obsidian-vault pointe vers tmp dir ✅
**Sévérité** : 🟠 HAUTE (config incorrecte, fallback silencieux)
**Découvert** : 2026-04-13 (audit Opus)
**Statut** : `resolved` (2026-04-13 ~11h00)
**Fichier** : `~/.claude/mcp.json`
**Détail** : Pointait vers `/var/folders/.../tmp.hdWpzdR59A/` qui n'existe plus (vérifié `ls` → No such file). Les Read passaient par l'outil natif en fallback.
**Actions réalisées** :
1. ✅ Vérifié que tmpdir n'existe pas (`test -d ... → MISSING`)
2. ✅ MCP `obsidian-vault` retiré entièrement de `~/.claude/mcp.json` (mcpServers vidé)
3. ✅ Référence `obsidian-vault` retirée de `enabledMcpjsonServers` projet
4. ✅ Note future-implementation créée pour [[future-mcp-obsidian-server]] (install MarkusPfundstein quand besoin)
**Plan futur** : voir [[future-mcp-obsidian-server]] — install obsidian-mcp-server (MarkusPfundstein 3k+ stars) dans une session dédiée (~30-45 min) si workflows tag-based / backlinks deviennent récurrents.

### TD-2026-006 — 79 règles permissions accumulées ⚠️ PARTIELLEMENT FAUX POSITIF
**Sévérité** : 🟡 MOYENNE (dette de config)
**Découvert** : 2026-04-13 (audit Opus)
**Statut** : `wontfix` (2026-04-13) — pas de worktrees obsolètes trouvés
**Fichier** : `.claude/settings.local.json`
**Détail audit** : "règles figées sur worktrees obsolètes (`/Users/djemildavid/Documents/Claude/Projects/second-brain/.worktrees/…`)"
**Vérification 2026-04-13** : `grep "worktree\|/Users/djemildavid/Documents/Claude/Projects"` → 0 résultat. Faux positif de l'audit.
**État réel** : ~91 règles, toutes pertinentes (commandes pipeline + permissions ciblées). Croissance organique normale due au mode acceptEdits actif.
**Note** : croissance attendue dans le temps (chaque commande nouvelle ajoute une règle). Pas de purge nécessaire tant que les règles correspondent à des paths/commandes valides.

### TD-2026-016 — integrity-check.sh à migrer vers Python ✅
**Sévérité** : 🟠 HAUTE (parsing fragile + race condition)
**Découvert** : 2026-04-13 (audit Opus bash/python)
**Statut** : `resolved` (2026-04-13 ~11h50)
**Fichier** : `integrity-check.sh` → `integrity_check.py` (432 lignes) + `tests/test_integrity_check.py` (43 tests)
**Actions réalisées** :
1. ✅ `integrity_check.py` créé (~400 LOC) avec 3 couches : pure functions / vault ops / subprocess wrappers
2. ✅ `tests/test_integrity_check.py` : **43 tests pytest, 100% PASS en 0.06s**
3. ✅ Fix parsing frontmatter : `extract_title()` saute le YAML frontmatter (regex `^---\n...\n---`)
4. ✅ Fix wikilinks : `re.findall(r'\[\[([^\]\n]+)\]\]')` robuste multi-lignes, aliases, paths
5. ✅ Fix race `/tmp/nightly.tmp` : `tempfile.mkstemp()` dans `_logs/` + `os.replace()` atomic
6. ✅ `nightly-agent.sh` updated : appelle `python3 integrity_check.py`
7. ✅ `integrity-check.sh` → `.deprecated` (rollback 1 semaine)
**Découverte bonus** : l'ancien bash produisait `[---](path)` pour TOUTES les notes avec frontmatter YAML (lisait la 1ère ligne `---`). Le INDEX.md était **corrompu depuis toujours** — maintenant fixé.
**Comparaison bash vs Python sur vault réel** :
- Bash : 10 wikilinks cassés détectés (dont 1 faux positif `[[note|alias]]`)
- Python : 9 wikilinks cassés (vrais positifs uniquement)
- INDEX.md : titres correctement extraits pour toutes les notes avec frontmatter

---

## 🟡 Moyennes (sprint courant ou suivant)

### TD-2026-007 — Plugins installés non utilisés (pollution contexte) ✅
**Sévérité** : 🟡 MOYENNE (performance)
**Découvert** : 2026-04-13 (audit Opus)
**Statut** : `resolved` (2026-04-13 ~10h45)
**Fichier** : `~/.claude/settings.json`
**Détail** : 3 plugins installés mais jamais utilisés pour Second Brain.
**Actions réalisées** :
1. ✅ `feature-dev@claude-plugins-official` → désactivé (doublon `superpowers:writing-plans`)
2. ✅ `code-review@claude-plugins-official` → désactivé (doublon `superpowers:requesting-code-review`)
3. ✅ `playwright@claude-plugins-official` → désactivé (24 MCP tools en moins du contexte)
**Approche** : désactivation via `enabledPlugins: false` (réversible). Cache disque conservé — peut être purgé plus tard si besoin.
**Plugins gardés actifs** : `superpowers`, `claude-mem`, `context7`. Plugin `github` reste désactivé user-level mais activé project-level via `enabledMcpjsonServers`.

### TD-2026-008 — Redondance plan/execute claude-mem vs superpowers
**Sévérité** : 🟡 MOYENNE (confusion workflow)
**Découvert** : 2026-04-13 (audit Opus)
**Statut** : `open`
**Détail** : Deux axes concurrents :
- `claude-mem:make-plan` + `claude-mem:do`
- `superpowers:writing-plans` + `superpowers:executing-plans`
Philosophies divergentes (orchestrator-subagent vs plan TDD).
**Action** : Choisir un axe et désactiver l'autre.

### TD-2026-009 — Log rotation manuelle nightly-agent
**Sévérité** : 🟡 MOYENNE (dette opérationnelle)
**Découvert** : 2026-04-13 (audit Opus)
**Statut** : `open`
**Détail** : `_logs/nightly-agent.log.1` à `.log.5` — rotation manuelle ou ad-hoc, pas via `logrotate`.
**Action** : Intégrer rotation propre dans `nightly-agent.sh` ou via launchd plist.

### TD-2026-010 — Hook claude-mem SessionStart peut bloquer 8s
**Sévérité** : 🟡 MOYENNE (UX)
**Découvert** : 2026-04-13 (audit Opus)
**Statut** : `open`
**Détail** : `sleep 1` dans boucle retry (8×) → ouverture session potentiellement bloquée 8s si worker claude-mem down.
**Action** : Reporter upstream ou wrapper avec timeout court.

### TD-2026-011 — Backups / file-history sans TTL
**Sévérité** : 🟡 MOYENNE (stockage + sécurité)
**Découvert** : 2026-04-13 (audit Opus)
**Statut** : `open`
**Détail** : `~/.claude/backups/` (6 dossiers, 2 semaines) et `~/.claude/file-history/` (33 dossiers) sans mécanisme de purge. Contient probablement des anciens secrets (TD-2026-001, TD-2026-002).
**Action** : Script de purge `find ~/.claude/backups -mtime +7 -delete`, idem file-history.

### TD-2026-012 — Audit qualité one-off non-automatisé
**Sévérité** : 🟢 BASSE (workflow)
**Découvert** : 2026-04-13 (audit Opus)
**Statut** : `open`
**Détail** : `_logs/audit-qualite-2026-04-12.md` généré à la main. Devrait être produit par skill `/nightly-triage`.
**Action** : Couvert par création du skill (voir [[audit-setup-claude-code-2026-04-13]] Phase 3).

### TD-2026-017 — nightly-agent.sh masque échec rsync critique ✅
**Sévérité** : 🟡 MOYENNE (data integrity)
**Découvert** : 2026-04-13 (audit Opus bash/python)
**Statut** : `resolved` (2026-04-13 ~11h50)
**Fichier** : `nightly-agent.sh` L.59-67
**Actions réalisées** :
1. ✅ `integrity_check.py` mode `--strict` ON par défaut — rsync fail = `RuntimeError` → `exit 1`
2. ✅ `nightly-agent.sh` inspecte `$INTEGRITY_RC` :
   - Exit 0 : OK, on continue
   - Exit 2 : conflits iCloud → stop avec code 2 (action manuelle requise)
   - Exit ≠ 0 : **stop avec code 1** (plus de continuation silencieuse sur vault corrompu)
3. ✅ Option `--best-effort` disponible pour rétro-compat si jamais besoin

### TD-2026-018 — nightly-agent.sh trap EXIT ne couvre pas SIGKILL
**Sévérité** : 🟡 MOYENNE (race condition / blocage silencieux)
**Découvert** : 2026-04-13 (audit Opus bash/python)
**Statut** : `open`
**Fichier** : `nightly-agent.sh` L.23
**Détail** : Le lock mkdir est nettoyé via `trap "rmdir $LOCKDIR" EXIT`. Mais :
- `kill -9` ne déclenche pas trap
- Crash launchd / SIGBUS / OOM → lock orphelin
- Les nuits suivantes : `mkdir` échoue → `exit 0` silencieux → aucune synthèse, aucun alert
**Action** :
- Ajouter détection d'âge du lock (si > 24h → considérer orphelin + alert)
- Ou : utiliser PID dans le lock + vérifier `kill -0 $pid` au mount
- Ou : ajouter un healthcheck cron séparé (`launchctl list` + last-nightly.json age)
**Priorité** : Sprint 2 ou 3

---

## 🟢 Basses (nice-to-have)

### TD-2026-013 — 30 langues de mode files claude-mem (bagage)
**Sévérité** : 🟢 BASSE
**Découvert** : 2026-04-13 (audit Opus)
**Statut** : `accepted` (plugin upstream, non modifiable)
**Détail** : `code--ar.json` à `code--zh.json`. Seul `code--fr.json` utile.
**Action** : Aucune (chargement lazy, impact nul).

### TD-2026-014 — Orphans + broken wikilinks en backlog
**Sévérité** : 🟢 BASSE (qualité vault)
**Découvert** : 2026-04-11 (obs #931)
**Statut** : `open`
**Détail** : 6 orphans + 7 broken wikilinks détectés par nightly, non résolus.
**Action** : Skill `/orphan-linker` custom (voir audit Phase 3 suite possible).

### TD-2026-015 — Skills claude-mem sous-utilisés
**Sévérité** : 🟢 BASSE (pollution namespace)
**Découvert** : 2026-04-13 (audit Opus)
**Statut** : `accepted`
**Détail** : `knowledge-agent`, `timeline-report`, `version-bump`, `smart-explore` jamais appelés dans logs. Conçus pour dev plugins, pas Second Brain.
**Action** : Aucune — cohabitent sans nuire.

### TD-2026-020 — Test coverage hétérogène sur modules Python pipeline
**Sévérité** : 🟡 MOYENNE (les 2 modules critiques `paper_synthesizer` et `corpus_collector` sont < 25%)
**Découvert** : 2026-04-14 (quick wins audit post-Sprint 2)
**Statut** : `open`
**Détail** :

| Module | Src lines | Test lines | Ratio line | Coverage réelle |
|--------|-----------|------------|------------|-----------------|
| `moc_freshness.py` | 223 | 224 | 100% | Excellente (TDD strict) |
| `integrity_check.py` | 524 | 433 | 83% | Solide |
| `notebooklm_weekly.py` | 681 | 311 | 46% | Moyenne |
| `corpus_collector.py` | 519 | 106 | 20% | 🚨 Faible |
| `paper_synthesizer.py` | 678 | 95 | 14% | 🚨 Critique |

Le module le plus exposé (paper_synthesizer avec Anthropic Batch API externe) a la couverture la plus basse. Le bug 64-char custom_id découvert empiriquement 2026-04-14 (TD-2026-019 fix) aurait été attrapé par un test d'intégration minimal.

Cible proposée :
- Modules critiques (paper_synth, corpus_collector) : ≥ 40% branch coverage avec `pytest-cov`
- Modules secondaires : ≥ 30%
- Modules core (integrity, moc_freshness) : garder > 80%

**Action** :
1. `pip install pytest-cov` (mesure réelle, pas ratio ligne)
2. Ajouter `pytest --cov=. --cov-fail-under=40 --cov-report=term-missing` à CI quand on aura CI
3. Prioriser tests sur `paper_synthesizer.submit_batch()` (mock Anthropic client), `process_batch_results()`, `parse_frontmatter_preamble()`

Coût marginal faible (couches à tester sont pures Python, mockable sans infra), grosse valeur préventive.

### TD-2026-019 — paper_synthesizer.py orphelin (jamais branché en prod) ✅
**Sévérité** : 🟠 HAUTE (664 lignes Python + Anthropic Batch API + 47 papers backlog jamais traités)
**Découvert** : 2026-04-13 (audit Opus, test empirique nightly run)
**Statut** : `resolved` (2026-04-14)
**Détail** : Script requiert `ANTHROPIC_API_KEY` env var (line 645) sans plomberie pour l'export.

**Actions réalisées** (option γ choisie) :
1. ✅ Clé Anthropic stockée dans Keychain : `security add-generic-password -U -a $USER -s anthropic-api-key -w "sk-ant-..."`
2. ✅ Wrapper `paper-synthesizer.sh` créé (commit `9932499`), charge depuis Keychain avec fail-fast + format check
3. ✅ Bug `custom_id > 64 chars` découvert empiriquement au 1er run (Anthropic Batch API limit) — fix TDD `_batch_custom_id()` md5 hash + 3 regression tests (commit `0aa9c6b`)
4. ✅ Run validation sur 45 papers (2026-04-14, ~1h, 0 erreur, ~$1) :
   - 87 concepts extraits (31 Tier S, 54 Tier A, 2 B)
   - 4 digests créés (ai/iot/cloud/ecommerce W16)
   - Qualité production-grade : titres déclaratifs Matuschak-style, frontmatter complet, simple_explanation plain-language
5. ✅ Connecté à launchd via `_meta/launchd/com.second-brain.papers-weekly.plist` (dimanche 10h00)

**Verdict empirique** : pipeline délivre de la valeur quand il tourne. Décision = connecter (pas supprimer). Karpathy approach validé via mesure plutôt qu'idéologie.

**Pipeline désormais bouclé** :
```
corpus_collector (manuel/orphan TD-021) → _inbox/raw/papers/
        ↓
paper-synthesizer.sh (dimanche 10h via launchd) → _inbox/raw/concepts/A-*.md
        ↓
nightly LLM (2h17 quotidien, étape 2A, cap 15/run FIFO) → vault notes
```

### TD-2026-021 — corpus_collector.py orphelin (papers n'arrivent pas seuls) ✅
**Sévérité** : 🟠 HAUTE (sans collecteur scheduled, le pipeline tourne à vide)
**Découvert** : 2026-04-14 (audit pipeline scheduling post-TD-019 résolu)
**Statut** : `resolved` (2026-04-14 14h00)
**Détail** : Script Python (519 LOC) qui fetch papers depuis arXiv + Semantic Scholar vers `_inbox/raw/papers/<domain>/`. Aucun plist launchd ne l'invoquait. Pipeline alimenté manuellement par dépôts user.

**Actions réalisées** :
1. ✅ Audit `corpus_collector.py --help` :
   - `--max 5/domain` default, `--since 30d`, `--min-score 0.3`, 4 domains = ~20 papers/run
   - Aucune clé API requise (arXiv + S2 publics, S2 peut return 429 sans key, fallback arXiv suffit)
2. ✅ Test fetch validation : 1 paper AI Tier A score 0.70 sauvé en `_inbox/raw/papers/ai/...`
3. ✅ Plist créé `_meta/launchd/com.second-brain.papers-fetch.plist`
   - Cadence : samedi 8h00 (avant weekly-extractor 9h, avant paper-synth dim 10h)
   - Sans dépendance API key (pas de Keychain à monter)
   - Note : à la fin, corpus_collector appelle automatiquement `corpus-rebuild.sh` (TD-023 dead code) avec `check=False` → échec silencieux non bloquant

**Pipeline weekly désormais bouclé** :
```
Sam 8h00  : corpus_collector → fetch ~20 papers → _inbox/raw/papers/
Sam 9h00  : weekly-extractor (existant)         → claude-mem extraction
Dim 10h00 : paper-synthesizer (TD-019 résolu)   → concepts atomiques
Lun 2h17+ : nightly LLM (cap 15/run FIFO)        → vault notes
```

Premier cycle complet : samedi 18 avril 2026.

### TD-2026-022 — notebooklm_weekly.py orphelin (Track B dormant)
**Sévérité** : 🟡 MOYENNE (681 LOC + 26 tests + wrapper shell, jamais scheduled)
**Découvert** : 2026-04-14 (audit pipeline scheduling)
**Statut** : `open`
**Détail** : `notebooklm_weekly.py` (681 LOC, 45% test coverage) + `notebooklm-weekly.sh` (wrapper avec deadline 23:30, caffeinate, status sentinel) sont conçus pour Track B (NotebookLM grounded synthesis). Le wrapper existe mais aucun plist ne l'invoque. Track B reste donc inactif (`enrichment_status.track_b_active: false` dans last-nightly.json).

Pré-requis vérifiés : `nlm-notebooks.json`, `nlm-status.json`, `_inbox/overflow/`, `_inbox/quarantine/` existent (bootstrap commit `ca70695` du Sprint 2). Variable `NLM_MCP_CMD` requise selon docstring.

**Action proposée** :
1. Vérifier auth NotebookLM (`auth.json`) configuré
2. Vérifier MCP server NLM disponible (`mcp__notebooklm__*` tools listés mais peut-être inactifs)
3. Décider : activer Track B (créer plist dimanche 22h, deadline 23:30) ou marquer feature comme "future, pas activée pour l'instant" → selon que le user veut Track B grounded ou pas
4. Si activé : créer `com.second-brain.nlm-weekly.plist`

Lié : `_meta/notebooklm-context-{ai,iot,cloud,ecommerce,global}.md` existent et sont updated par nightly. Mais sans Track B exécuté, ces contextes ne sont jamais lus par NLM.

### TD-2026-023 — corpus-rebuild.sh dead code (0 obs indexed)
**Sévérité** : 🟢 BASSE (cosmétique, ne casse rien mais pollue)
**Découvert** : 2026-04-14 (audit scheduling, log review)
**Statut** : `open`
**Détail** : `corpus-rebuild.sh` (1939 bytes) tente de reconstruire le corpus claude-mem `research-papers` via `mcp__plugin_claude-mem_mcp-search__build_corpus`. Le log `_logs/corpus-rebuild.log` documente 3 runs manuels (2026-04-11) qui retournent tous **0 fichiers indexés**. Note explicite dans le log :
> Le paramètre `path` n'est pas supporté nativement par `build_corpus` — il filtre des observations claude-mem, pas des fichiers filesystem. Les papiers dans `_inbox/raw/papers/` ne sont pas encore traités par le pipeline d'extraction.

Donc le script ne marche pas par design — il essaie de faire qqch que `build_corpus` ne supporte pas. C'est du code mort confirmé.

**Action proposée** :
1. Supprimer `corpus-rebuild.sh` + commit avec rationale
2. Si on veut vraiment indexer les papers dans claude-mem, c'est un autre design (probablement écrire un script qui INGEST chaque .md comme observation puis rebuild)
3. Pour l'instant, paper_synthesizer + nightly LLM remplit le rôle "papers → connaissance utilisable" sans avoir besoin de claude-mem indexing

---

## ✅ Résolus

### 2026-04-13 — Phase 1 (sécurité)
- **TD-2026-001** — GitHub PAT exposé → ✅ révoqué + migré vers macOS Keychain
- **TD-2026-002** — 2 Google API Keys exposées → ✅ révoquées + retirées (user n'utilise plus Google API)

### 2026-04-13 — Phase 2 (nettoyage)
- **TD-2026-003** — Permissions trop larges → ✅ 5 patterns dangereux retirés (`Bash(python3 -c ':*)`, `pip3 install`, `brew install`, `Read(//Users/**)`, `Read(//opt/homebrew/**)`)
- **TD-2026-005** — MCP obsidian-vault cassé (tmpdir mort) → ✅ retiré + note future-implementation `[[future-mcp-obsidian-server]]` créée
- **TD-2026-007** — 3 plugins inutiles → ✅ désactivés (`feature-dev`, `code-review`, `playwright`)

### 2026-04-13 — Phase 4 (migration bash → Python)
- **TD-2026-016** — `integrity-check.sh` migré vers `integrity_check.py` (43 tests pytest, 100% pass) + **découverte bonus** : le bash produisait `[---](path)` pour toutes les notes avec frontmatter YAML (INDEX.md corrompu depuis toujours, maintenant fixé)
- **TD-2026-017** — Masquage silencieux des échecs dans nightly-agent.sh → ✅ mode `--strict` ON par défaut, exit 1 si intégrité échoue

## ❌ Wontfix (faux positifs audit)

- **TD-2026-004** — `/notebooklm-weekly` "stub 1 ligne" → faux positif : 384 lignes, skill complet
- **TD-2026-006** — Règles permissions sur worktrees obsolètes → faux positif : aucune référence trouvée

---

## Vue d'ensemble

| Sévérité | Ouverts | Acceptés | Résolus | Wontfix |
|----------|---------|----------|---------|---------|
| 🔴 Critique | 0 | 0 | 2 | 0 |
| 🟠 Haute | 0 | 0 | 3 | 1 |
| 🟡 Moyenne | 5 | 0 | 2 | 1 |
| 🟢 Basse | 2 | 2 | 0 | 0 |
| **Total** | **7** | **2** | **7** | **2** |

**Progression Phase 1 + 2 + 4 (2026-04-13)** :
- ✅ **Phase 1 (sécurité)** : TD-001, TD-002
- ✅ **Phase 2 (nettoyage)** : TD-003, TD-005, TD-007
- ✅ **Phase 4 (migration bash→Python)** : TD-016, TD-017
- ❌ Wontfix : TD-004 (faux positif), TD-006 (faux positif worktrees)

**🎉 Plus aucune dette critique NI haute ouverte.** Il reste uniquement des dettes Moyennes (5) et Basses (2).

---

## Conventions

- **ID** : `TD-YYYY-NNN` (3 digits, séquence annuelle)
- **Sévérité** : 🔴 Critique → action immédiate / 🟠 Haute → cette semaine / 🟡 Moyenne → sprint / 🟢 Basse → nice-to-have
- **Statut** : `open` / `in-progress` / `resolved` / `accepted` (accepté comme dette permanente) / `wontfix`
- **Champs obligatoires** : Sévérité, Découvert, Statut, Détail, Action

## Process

1. Chaque nouvelle dette découverte → ajouter entrée ici
2. Résolution → déplacer vers section "Résolus" + commit référence
3. Audit trimestriel → re-prioriser

## Liens
- [[audit-setup-claude-code-2026-04-13]] — audit source principal
- [[future-managed-agents-anthropic]] — considération long terme

## Tags
#tech-debt #registry #tracking #security
