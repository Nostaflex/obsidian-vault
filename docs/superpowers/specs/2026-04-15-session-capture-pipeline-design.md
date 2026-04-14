# Session Capture Pipeline — Design Spec

**Date** : 2026-04-15  
**Statut** : Draft — pending user review  
**Auteur** : Djemil David + Claude Sonnet 4.6  
**Motivations** : combler le gap de mémoire épisodique du vault sans dépendance externe (MemPalace écarte), survivre aux compacts de contexte, capturer les décisions en temps réel.

---

## 1. Contexte et problème

### 1.1 Gap identifié

Le vault Second Brain excelle en mémoire **déclarative** (notes atomiques, wikilinks, MOCs). Il est aveugle à la mémoire **épisodique** : les décisions prises en session interactive, leur contexte, leur ordre, les alternatives écartées. Cette dimension disparaît entre sessions.

Les mécanismes existants ne comblent pas ce gap :

| Mécanisme | Ce qu'il capture | Ce qu'il manque |
|-----------|-----------------|-----------------|
| `session_pointer.md` | État git, branche, PRs ouvertes | Décisions, intentions, contexte |
| `claude-mem` | Observations structurées | Accessible en session interactive seulement (pas `--print`) |
| `weekly extractor` | Concepts depuis claude-mem | Latence 7 jours max, dépend du weekly run |
| `_inbox/session/` manuelles | Décisions si rédigées manuellement | Effort humain, non systématique |

### 1.2 Contraintes architecturales non-négociables

- **Zéro service externe** — pas de ChromaDB, pas d'API tier, tout reste dans le vault git
- **Zéro modification de l'existant** — `session-end-checkpoint.sh` et le nightly prompt ne sont pas touchés
- **Light Mode préservé** — pas de LLM call dans les hooks (trop lent, trop coûteux, trop fragile)
- **Philosophie vault** — tout ce qui compte finit en note markdown versionnée, traceable, intégrable par le nightly
- **Survie au compact** — la capture ne dépend pas de la continuité du contexte conversationnel

### 1.3 Données empiriques (sessions réelles)

| Métrique | Valeur | Source |
|----------|--------|--------|
| Assistant turns par session | ~119 (session typique) | JSONL 639e19b9 |
| Delta moyen entre Stop events | 2.7 lignes | Session 6b2b00a3 (2932 lignes) |
| Delta max entre Stop events | 48 lignes | Idem |
| Tool calls / décisions user | 2:1 (63 tools / 31 décisions) | Session 639e19b9 |
| Taille JSONL typique | 300KB–900KB | 13 sessions analysées |
| Taille JSONL max observée | 8MB (2159 lignes) | Session 3731af19 |

---

## 2. Architecture

### 2.1 Vue d'ensemble

```
[Session interactive]
    │
    ├─ [Stop hook — chaque réponse Claude]
    │      session-stop-capture.sh
    │           → pre-filter shell (< 1ms si pas de delta utile)
    │           → session-extractor.py (si delta utile)
    │                → read_delta(last_offset)          # O(nouvelles lignes)
    │                → apply_privacy_filter()
    │                → detect_decision_closures()
    │                → append_to_wip()                  # append-only, atomique
    │                → update_checkpoint()
    │                → log
    │
    ├─ [SessionEnd hook — fin de session]
    │      session-end-checkpoint.sh                    # INCHANGÉ → session_pointer.md
    │      session-transcript-finalizer.sh              # NOUVEAU
    │           → rename wip-{id}.md → session-YYYY-MM-DD-{id}.md
    │           → cleanup session-checkpoint.json
    │           → log
    │
    └─ [Nightly agent — 2h17]
           Étape 1 : traite _inbox/session/session-*.md  # INCHANGÉ
                → mitose cognitive
                → notes atomiques dans vault
                → LOG.md anti-réingestion
```

### 2.2 Séparation des responsabilités

| Composant | Responsabilité unique | Timeout | Modifie l'existant |
|-----------|----------------------|---------|-------------------|
| `session-end-checkpoint.sh` | Git state → `session_pointer.md` | 10s | Non |
| `session-stop-capture.sh` | Orchestration du Stop hook | 15s | Non |
| `session-extractor.py` | Parse JSONL delta → append WIP | < 5s | Non |
| `session-transcript-finalizer.sh` | WIP → note finalisée | 10s | Non |
| Nightly agent | Mitose cognitive des notes session | Existant | Non |

### 2.3 Fichiers produits et leur cycle de vie

```
_logs/
  session-checkpoint.json      # état courant du Stop hook (écrasé à chaque Stop)
  session-extractor.log        # log append-only (rotation à 1MB)

_inbox/session/
  wip-{session_id[:6]}.md      # note en cours (ignorée par nightly — préfixe wip-)
  session-YYYY-MM-DD-{id}.md   # note finalisée (traitée par nightly)
  _processed/                  # après traitement nightly
```

---

## 3. Composants détaillés

### 3.1 `session-stop-capture.sh` — Stop hook orchestrateur

**Responsabilité :** pre-filter rapide + délégation à Python si nécessaire.

**Logique :**

```bash
# 1. Parser le payload stdin → session_id + transcript_path
payload=$(cat)
session_id=$(echo "$payload" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('session_id',''))" 2>/dev/null)
transcript_path=$(echo "$payload" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('transcript_path',''))" 2>/dev/null)

# 2. Fallback découverte si transcript_path absent
if [ -z "$transcript_path" ] || [ ! -f "$transcript_path" ]; then
  transcript_path=$(ls -t ~/.claude/projects/$(basename "$(pwd)" | sed 's|/|-|g')-*/*.jsonl 2>/dev/null | head -1)
  # Fallback robuste : chercher par mtime dans tous les projets claude du vault
  [ -z "$transcript_path" ] && transcript_path=$(find ~/.claude/projects/ -name "*.jsonl" -newer "$CHECKPOINT" 2>/dev/null | head -1)
fi

# 3. Pre-filter shell : lire last_offset depuis checkpoint
last_offset=$(jq -r '.last_offset // 0' "$CHECKPOINT" 2>/dev/null || echo 0)
current_lines=$(wc -l < "$transcript_path" 2>/dev/null || echo 0)
delta=$((current_lines - last_offset))

# 4. Skip si delta insuffisant (< 3 lignes = pas de nouvel échange complet)
[ "$delta" -lt 3 ] && exit 0

# 5. Déléguer à Python
python3 "$VAULT/_tools/session-extractor.py" \
  --transcript "$transcript_path" \
  --session-id "$session_id" \
  --checkpoint "$CHECKPOINT" \
  --wip-dir "$VAULT/_inbox/session" \
  --log "$LOG"
```

### 3.2 `session-extractor.py` — Extracteur Python

**Responsabilité :** parse delta JSONL → detection décisions → append WIP.

**Pipeline interne (fonctions pures, testables indépendamment) :**

```python
def parse_delta(transcript_path: str, last_offset: int) -> list[dict]:
    """Lit uniquement les lignes depuis last_offset. O(delta)."""

def apply_privacy_filter(messages: list[dict]) -> list[dict]:
    """Redacte patterns sensibles : .nosync, tokens, URLs credentials."""
    PATTERNS = [r'\.nosync', r'work\.nosync', r'confidentiel',
                r'sk-[a-zA-Z0-9]{20,}', r'Bearer\s+\S+', r'password\s*[:=]']

def score_message(msg: dict, prev_assistant: str) -> float:
    """
    Score de valeur décisionnelle 0.0–1.0.
    
    Amplificateurs (message user court après proposition assistant) :
      - "oui"/"go"/"ok"/"validé"/"parfait" → score += 0.8
    
    Signaux positifs :
      - Message user > 20 chars : +0.3
      - Réponse assistant > 200 chars : +0.2  
      - Tool calls dans le tour (Bash/Edit/Write) : +0.3
      - Patterns clôture dans assistant ("mergé", "déplacé", "commité") : +0.2
    
    Signaux négatifs :
      - Message commence par '#' (skill invocation) : score = 0.0
      - Message est task-notification XML : score = 0.0
      - Message < 4 chars sans amplificateur : score = 0.0
    """

def detect_decision_closures(scored_messages: list) -> list[dict]:
    """
    Retourne les paires (intention, contexte) avec score > 0.5.
    Chaque paire = {user_text, assistant_summary, tools_called, score, timestamp}
    """

def render_wip_delta(decisions: list[dict], session_id: str) -> str:
    """Formate le delta en markdown append-friendly."""

def append_to_wip(wip_path: str, content: str) -> None:
    """Append atomique via write-temp + rename."""

def update_checkpoint(checkpoint_path: str, session_id: str,
                      transcript_path: str, new_offset: int,
                      wip_path: str) -> None:
    """Écrit {session_id, last_offset, transcript_path, wip_path, started_at}."""
```

### 3.3 Format de la note WIP

```markdown
---
type: session-wip
session_id: 639e19b9
started_at: 2026-04-14T22:22:53Z
status: in-progress
tags: []
---

# Session WIP — 639e19b

<!-- extractor-debug: last_offset=483, delta=47, decisions_captured=3, score_threshold=0.5 -->

## [22:31] go tier A → go tier B
**Intention** : vider l'overflow (70 concepts) vers raw/concepts
**Action** : 44 fichiers A-tier + 2 B-tier déplacés
**Tools** : Bash ×3

## [22:34] lancer le nightly en parallèle
**Intention** : forcer run nightly (bypass guard UTC last_run)
**Action** : last_run modifié → 2026-04-13, nightly lancé background
**Tools** : Bash ×4

## [22:37] merger les 3 PRs ouvertes
**Intention** : PRs #18 #19 #20 → main
**Action** : gh pr merge ×3, git pull rebase
**Tools** : Bash ×5

<!-- extractor-debug: last_offset=530, delta=38, decisions_captured=1, score_threshold=0.5 -->

## [22:52] MemPalace écarté — approche native préférée
**Intention** : analyser MemPalace vs architecture vault
**Action** : analyse architecturale, décision : pas d'install
**Tools** : WebSearch ×1
```

### 3.4 `session-transcript-finalizer.sh` — SessionEnd finalizer

**Responsabilité :** WIP → note finalisée + cleanup.

```bash
# 1. Lire le checkpoint pour retrouver le wip_path
wip_path=$(jq -r '.wip_path // ""' "$CHECKPOINT" 2>/dev/null)

# 2. Si pas de WIP (session sans décisions capturées) → exit propre
[ -z "$wip_path" ] || [ ! -f "$wip_path" ] && exit 0

# 3. Rename atomique WIP → note finalisée
date_str=$(date +%Y-%m-%d)
session_short=$(jq -r '.session_id' "$CHECKPOINT" 2>/dev/null | cut -c1-6)
final_name="session-${date_str}-${session_short}.md"
final_path="$VAULT/_inbox/session/$final_name"

# Mettre à jour le frontmatter status
sed -i '' 's/status: in-progress/status: complete/' "$wip_path"
mv "$wip_path" "$final_path"   # atomique sur même filesystem

# 4. Cleanup checkpoint
rm -f "$CHECKPOINT"

# 5. Log
echo "$(date -u +%FT%TZ) finalized: $final_name" >> "$LOG"
```

---

## 4. Gestion des edge cases

### 4.1 Crash ou kill -9 pendant une session

**Situation :** session fermée brutalement, SessionEnd ne se déclenche pas.  
**Impact :** WIP existe avec tout ce qui a été capturé jusqu'au dernier Stop. Le checkpoint est valide.  
**Résolution :** au prochain SessionStart, le checkpoint orphelin est détecté. Le WIP est renommé avec la date du jour et déposé en `_inbox/session/`. Le nightly le traite le soir.

**Implémentation :** ajouter dans le `SessionStart` hook (ou un hook dédié) :
```bash
# Si checkpoint orphelin détecté (session_id différent de la session courante)
# → finaliser le WIP orphelin avant de démarrer
```

### 4.2 Compact de contexte mid-session

**Situation :** Claude Code compacte automatiquement, le session_id peut changer.  
**Impact potentiel :** le Stop hook post-compact utilise un nouveau session_id → nouveau WIP créé, l'ancien WIP orphelin.  
**Fix :** le checkpoint stocke `started_at` + `project_path`. Au démarrage du Stop hook, si un WIP orphelin existe pour le même `project_path` + même jour → continuer à appender sur ce WIP plutôt qu'en créer un nouveau.

### 4.3 Deux sessions le même jour

**Situation :** session matin + session soir sur le même projet.  
**Impact :** les deux produisent `session-2026-04-15-{id}.md` avec des `id` différents → pas de collision.  
**Note :** le nightly traite les deux séparément → deux jeux de notes atomiques potentiellement redondants. Acceptable — le nightly détecte les doublons via LOG.md.

### 4.4 JSONL absent ou corrompu

**Situation :** `transcript_path` absent du payload, fallback mtime échoue aussi.  
**Comportement :** exit 0 silencieux + log de l'échec. Aucun WIP créé. Aucun crash.

### 4.5 WIP ignoré par le nightly

**Garantie :** le nightly ignore tous les fichiers préfixés `wip-` dans `_inbox/session/`. Règle ajoutée au `.nightly-prompt.md` :
```
Dans _inbox/session/, ignorer les fichiers commençant par "wip-" (session en cours).
Traiter uniquement les fichiers commençant par "session-".
```

---

## 5. Privacy

### 5.1 Patterns bloquants (regex, appliqués avant tout traitement)

```python
PRIVACY_PATTERNS = [
    r'\.nosync',                    # chemins work.nosync / sensitive.nosync
    r'work\.nosync',
    r'confidentiel',                # marqueur vault existant
    r'sk-[a-zA-Z0-9]{20,}',        # API keys style OpenAI/Anthropic
    r'Bearer\s+\S{10,}',           # Authorization headers
    r'password\s*[:=]\s*\S+',      # passwords inline
    r'ghp_[a-zA-Z0-9]{36}',        # GitHub tokens
    r'-----BEGIN\s+\w+\s+KEY',     # clés privées
]
```

### 5.2 Comportement au hit

Le message entier est remplacé par `[redacted — privacy filter: {pattern_name}]`. Le delta est logué sans le contenu redacté.

### 5.3 Audit trail

Le bloc `<!-- extractor-debug -->` dans le WIP liste le nombre de messages redactés par delta sans révéler leur contenu.

---

## 6. Observabilité

### 6.1 `_logs/session-extractor.log`

Format append-only, rotation à 1MB :
```
2026-04-15T23:05:12Z | STOP | session=639e19b | delta=47l | decisions=3 | redacted=0 | 0.31s
2026-04-15T23:07:44Z | STOP | session=639e19b | delta=3l | skip (below threshold)
2026-04-15T23:09:11Z | FINALIZE | session=639e19b | wip→session-2026-04-15-639e19.md
2026-04-15T23:09:11Z | FINALIZE | decisions_total=7 | duration=0.08s
```

### 6.2 Bloc debug dans le WIP

Chaque append inclut un bloc HTML comment avec les métriques du delta. Visible à l'audit, strippé par le nightly avant ingestion.

### 6.3 Nightly maintenance-report

Ajouter au rapport nightly :
```
| Session traces | N notes session-* traitées | N décisions extraites |
```

---

## 7. Tests

### 7.1 Fixtures de test

- `tests/fixtures/session-short.jsonl` — 50 lignes, 5 décisions claires
- `tests/fixtures/session-compact.jsonl` — session avec break mid-stream simulé
- `tests/fixtures/session-privacy.jsonl` — messages avec patterns sensibles

### 7.2 Tests unitaires (pytest)

```python
def test_parse_delta_offset()          # vérifie que seules les nouvelles lignes sont lues
def test_privacy_filter_api_key()      # vérifie redaction sk-xxx
def test_privacy_filter_nosync()       # vérifie redaction .nosync paths
def test_score_amplifier_oui()         # "oui" après proposition → score > 0.5
def test_score_skill_invocation()      # message '#' → score = 0.0
def test_score_short_no_context()      # "go" sans contexte → score = 0.0
def test_detect_zero_decisions()       # session sans décisions → WIP non créé
def test_append_atomicity()            # write-temp + rename, jamais de fichier partiel
def test_checkpoint_orphan_recovery()  # WIP orphelin → finalisé au prochain start
```

### 7.3 Test d'intégration

Script `tests/test-stop-hook.sh` qui :
1. Crée un JSONL fixture avec `transcript_path` connu
2. Invoque `session-stop-capture.sh` avec payload JSON mocké
3. Vérifie existence et contenu du WIP
4. Invoque `session-transcript-finalizer.sh`
5. Vérifie renommage et cleanup checkpoint

---

## 8. Limites documentées

| Limite | Impact | Acceptable ? |
|--------|--------|-------------|
| Décisions implicites sans pattern de clôture | Capturées partiellement — nightly complète | Oui |
| Sessions multi-projets mélangées | Nightly démêle lors de la mitose | Oui |
| Compact change le session_id | Gestion via `project_path` + `started_at` | Oui |
| Pas de recall cross-sessions en temps réel | Hors scope — rôle de claude-mem + grep | Oui |
| Dernière décision au moment du compact potentiellement manquée | Perte maximale = 1 échange | Acceptable |

---

## 9. Fichiers à créer

```
_tools/
  session-stop-capture.sh          # Stop hook orchestrateur
  session-extractor.py             # Extracteur Python (fonctions pures)
  session-transcript-finalizer.sh  # SessionEnd finalizer

tests/
  test-stop-hook.sh                # Test intégration
  fixtures/
    session-short.jsonl
    session-compact.jsonl
    session-privacy.jsonl
  test_session_extractor.py        # Tests unitaires pytest

_logs/
  session-extractor.log            # créé au premier run (gitignored)
```

### Modification `.claude/settings.json`

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": ".*",
        "hooks": [{
          "type": "command",
          "command": "bash /Users/djemildavid/Documents/Obsidian/KnowledgeBase/_tools/session-stop-capture.sh",
          "timeout": 15
        }]
      }
    ],
    "SessionEnd": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "bash /Users/djemildavid/Documents/Obsidian/KnowledgeBase/_tools/session-end-checkpoint.sh",
            "timeout": 10
          },
          {
            "type": "command",
            "command": "bash /Users/djemildavid/Documents/Obsidian/KnowledgeBase/_tools/session-transcript-finalizer.sh",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

### Modification `.nightly-prompt.md`

Une ligne ajoutée à l'Étape 1 :
```
Dans _inbox/session/, ignorer les fichiers commençant par "wip-" (session en cours, non finalisée).
```

---

## 10. Décisions architecturales enregistrées

| Décision | Raison |
|----------|--------|
| Stop hook plutôt que SessionEnd seul | Survie au compact — capture incrémentale |
| Note WIP unique par session | Mitose déléguée au nightly LLM — pas à l'extracteur déterministe |
| Append-only sur WIP | Atomicité garantie, pas de corruption sur crash |
| Pas de LLM dans les hooks | Latence, coût, fragilité incompatibles avec un hook |
| Deux hooks SessionEnd indépendants | SRP — checkpoint git ≠ finalisation transcript |
| Fallback mtime si transcript_path absent | Robustesse sur edge cases hook payload |
| Privacy filter avant tout traitement | Defense-in-depth — données sensibles ne quittent jamais le script |
