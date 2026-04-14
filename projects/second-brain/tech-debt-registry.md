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

### TD-2026-019 — paper_synthesizer.py orphelin (jamais branché en prod)
**Sévérité** : 🟠 HAUTE (664 lignes Python + Anthropic Batch API + 47 papers en backlog ne sont jamais traités)
**Découvert** : 2026-04-13 (audit Opus, test empirique nightly run)
**Statut** : `open`
**Détail** : Script requiert `ANTHROPIC_API_KEY` env var (line 645) mais aucune plomberie ne l'export :
- ❌ Pas dans `~/Library/LaunchAgents/com.second-brain.nightly.plist` (env = juste PATH+HOME)
- ❌ Pas dans Keychain (cherché `anthropic-api-key`, `anthropic`)
- ❌ Pas dans `~/.zshrc` / `~/.bash_profile` / `~/.profile`
- ❌ `nightly-agent.sh` lance `claude --print` (auth Claude Code, pas API key Python SDK)

Conséquence : `_inbox/raw/papers/` accumule 47 papers depuis ~7 jours (W15 → W16) sans personne pour les processer en concepts atomiques. Le pipeline `corpus_collector → paper_synthesizer → MOC` est interrompu après collecte.

**Action proposée** (γ — choisi 2026-04-13 22:50) :
1. Stocker clé Anthropic dans Keychain (pattern `github-pat` éprouvé) :
   `security add-generic-password -U -a $USER -s anthropic-api-key -w "sk-ant-..."`
2. Wrapper `paper-synthesizer.sh` qui charge depuis Keychain + lance Python :
   ```bash
   #!/bin/bash
   export ANTHROPIC_API_KEY=$(security find-generic-password -a $USER -s anthropic-api-key -w)
   python3 "$(dirname "$0")/paper_synthesizer.py" "$@"
   ```
3. Ajouter au launchd plist hebdomadaire (`com.second-brain.weekly.plist`) ou intégrer à `nightly-agent.sh` après `integrity-check`.
4. Run de validation sur les 47 papers en attente (Anthropic Batch, ~$1-3 estimé)
5. Mesurer le résultat : si le pipeline complet (papers → concepts → MOC routing → /load-moc) délivre de la valeur, garder ; sinon supprimer (Karpathy approach : 664 lignes mortes ont un coût de maintenance > valeur).

**Décision stratégique attachée** : "on simplifiera à partir du résultat" (user 2026-04-13). Le finding empirique post-fix décide : connecter (γ valid) ou supprimer (validation forte du smell #3 over-engineered).

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
