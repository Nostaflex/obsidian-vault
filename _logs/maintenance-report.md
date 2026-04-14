# Maintenance Report — Knowledge Base

## Auto-corrections 2026-04-13
- `[[decision-bash-vs-python-boundary.md]]` → `[[decision-bash-vs-python-boundary]]` dans projects/second-brain/architecture-token-efficient-skills.md (suffixe .md retiré)
- `[[wiki]]` ajouté à lint-ignore.txt (exemple illustratif dans table de future-mcp-obsidian-server.md)

## Orphelines 2026-04-13
- Aucune éligible — toutes les notes ont < 30 jours (vault créé 2026-04-11)

## Wikilinks cassés 2026-04-13
- Tous les liens cassés restants sont couverts par lint-ignore.txt (exemples illustratifs)

## Candidats archivage 2026-04-13
- Aucun — toutes les notes ont < 90 jours

## Contradictions potentielles 2026-04-13
- Aucune détectée

## Review queue 2026-04-13
- weekly-review-W16.md déjà à jour (3 fleeting les plus anciennes du 2026-04-12)

---

## Orphelines 2026-04-11
Notes sans mention entrante dans `## Liens` d'autres notes :
- `projects/second-brain/anti-bug-claude-jsonl-schema.md`
- `universal/mcp-vscode-dedicated-file.md`
- `universal/pattern-subagent-driven-development.md`
- `projects/second-brain/anti-bug-grep-confidentiel-faux-positif.md`

Note : toutes créées ce run — normal pour un premier ingest massif. À relier au prochain run.

## Wikilinks cassés 2026-04-11
Source : `_logs/broken-links.txt` (détectés par integrity-check.sh)

| Wikilink cassé | Localisation probable | Correction suggérée |
|---|---|---|
| `[[ancienne-note]]` | `projects/second-brain/decisions/knowledge-graph-deferred.md` (Phase 1 exemple) | Supprimer ou remplacer par note réelle |
| `[[note-dépendante]]` | Idem (exemple Phase 1) | Idem |
| `[[note-opposée]]` | Idem (exemple Phase 1) | Idem |
| `[[wikilinks]]` | Idem (intro) | Remplacer par référence réelle |

Ces liens cassés sont des **exemples de template** dans `knowledge-graph-deferred.md`, pas de vrais liens brisés. Aucune action urgente requise — mais à clarifier lors de la prochaine révision de cette note.

## Candidats archivage 2026-04-11
Aucun — `_meta/signals.md` jamais alimenté. Fenêtre 90j non calculable.
Note structurelle : signals.md est vide (faille identifiée dans `discovery-vault-failles-audit.md`).

## Contradictions potentielles 2026-04-11
Aucune contradiction détectée entre les notes du run.

---

## Orphelines 2026-04-11 (run 2)
2 orphelines supplémentaires non détectées au run précédent :
- `projects/gpparts/anti-bug-checkout-race-condition.md` — mentionnée dans `_meta/context-gpparts.md` uniquement, jamais dans un `## Liens` d'une autre note
- `projects/second-brain/decisions/knowledge-graph-deferred.md` — aucune mention entrante dans les notes du vault

Total orphelines cumulées : 6

## Wikilinks cassés 2026-04-11 (run 2)
3 liens avec chemin partiel `decisions/…` — la note existe mais sous `projects/second-brain/decisions/` :

| Wikilink cassé | Note existante dans INDEX | Correction suggérée |
|---|---|---|
| `[[decisions/architecture-hybride-second-brain]]` | `projects/second-brain/decisions/architecture-hybride-second-brain.md` | Remplacer par `[[architecture-hybride-second-brain]]` |
| `[[decisions/vault-seed-runtime-pattern]]` | `projects/second-brain/decisions/vault-seed-runtime-pattern.md` | Remplacer par `[[vault-seed-runtime-pattern]]` |
| `[[decisions/weekly-extractor-approach-c]]` | `projects/second-brain/decisions/weekly-extractor-approach-c.md` | Remplacer par `[[weekly-extractor-approach-c]]` |

Ces 3 liens apparaissent dans plusieurs notes (architecture-dual-profile-vscode, anti-bug-claude-jsonl-schema, anti-bug-grep-confidentiel-faux-positif, discovery-mcp-tools-print-mode, discovery-claude-mem-privacy-risk, discovery-claude-mem-architecture). Correction manuelle recommandée — Obsidian résout par nom de fichier, pas par chemin relatif.

## Candidats archivage 2026-04-11 (run 2)
Aucun — `_meta/signals.md` toujours vide. Fenêtre 90j non calculable.

## Contradictions potentielles 2026-04-11 (run 2)
Aucune contradiction détectée.

---

## Orphelines 2026-04-12
Notes sans mention entrante dans `## Liens` d'autres notes (29 notes dans le vault) :
- `projects/gpparts/anti-bug-checkout-race-condition.md` — persistante (4ème run)
- `projects/second-brain/anti-bug-claude-jsonl-schema.md` — persistante
- `projects/second-brain/anti-bug-grep-confidentiel-faux-positif.md` — persistante
- `universal/mcp-vscode-dedicated-file.md` — persistante
- `universal/pattern-subagent-driven-development.md` — persistante
- `universal/research/digest-2026-W15.md` — aucun lien entrant (normal : digest hebdo)

Bonne nouvelle : `decisions/knowledge-graph-deferred.md` n'est plus orpheline — liée depuis `discovery-second-brain-v4-gaps-fixes.md`.

## Wikilinks cassés 2026-04-12
Situation identique au run précédent (7 liens cassés, tous connus) :
- 4 liens illustratifs dans `knowledge-graph-deferred.md` (exemples de template Phase 1) — aucune action
- 3 liens `decisions/…` avec chemin partiel — notes existent, résolution à corriger manuellement

## Candidats archivage 2026-04-12
`_meta/signals.md` toujours vide — fenêtre 90j non calculable. Pas de candidat identifiable.

## Contradictions potentielles 2026-04-12
Aucune contradiction détectée.


## Lint run 2026-04-12T12:35:00Z

### Orphelines 2026-04-12
Aucune note orpheline depuis >30 jours. Notes sans incoming links (toutes <30j) :
- universal/anti-bug-set-e-jq-missing-file.md — créée aujourd'hui
- universal/anti-bug-zip-executable-bit-lost.md — créée aujourd'hui
- projects/second-brain/decision-mind-free-kit-first-strategy.md — créée aujourd'hui
- universal/concept-context-preservation-after-mitosis.md — créée aujourd'hui

### Wikilinks cassés 2026-04-12
4 liens cassés détectés par integrity-check.sh — tous présents dans _meta/lint-ignore.txt (faux positifs documentés). Aucune action requise.

### Candidats archivage 2026-04-12
_meta/signals.md vide — fenêtre 90j non calculable. Aucun candidat.

### Contradictions potentielles 2026-04-12
Aucune contradiction détectée sur les 38 notes actives.

### Auto-corrections silencieuses 2026-04-12
4 liens nus annotés dans discovery-nightly-agent-architecture.md, decision-weekly-extractor-approach-c.md, discovery-mcp-tools-print-mode.md, pattern-inbox-raw-layer.md.

---

## Lint 2026-04-13

### Orphelines 2026-04-13
10 notes orphelines identifiées (aucune référencée dans ## Liens d'autres notes) :
- universal/research/digest-2026-W15.md
- universal/mcp-vscode-dedicated-file.md
- universal/pattern-subagent-driven-development.md
- universal/concept-context-preservation-after-mitosis.md
- universal/anti-bug-zip-executable-bit-lost.md
- universal/anti-bug-set-e-jq-missing-file.md
- projects/gpparts/anti-bug-checkout-race-condition.md
- projects/second-brain/anti-bug-grep-confidentiel-faux-positif.md
- projects/second-brain/anti-bug-claude-jsonl-schema.md
- projects/second-brain/decision-bash-vs-python-boundary.md

_Toutes créées < 30j — pas de marquage archive-candidate._

### Wikilinks cassés 2026-04-13
9 liens cassés détectés par integrity-check.sh — tous présents dans _meta/lint-ignore.txt (faux positifs documentés). 5 nouvelles entrées ajoutées à lint-ignore (note, future-managed-agents-anthropic|alias, tech-debt-registry#anchors). Aucune action requise.

### Candidats archivage 2026-04-13
Vault < 30j — aucun candidat éligible (fenêtre 90j).

### Contradictions potentielles 2026-04-13
Aucune contradiction détectée sur les 42 notes actives.

### Auto-corrections silencieuses 2026-04-13
0 corrections nécessaires (toutes les notes ont déjà ## Liens).

---

## Lint 2026-04-14

### Auto-corrections silencieuses 2026-04-14
1 correction : ajout `## Liens` manquant dans `universal/research/digest-ecommerce-W16.md`.
0 wikilink redirige (aucun lien casse vers un basename existant sous un autre nom).

### Orphelines 2026-04-14
15 notes orphelines identifiees (aucune referencee dans ## Liens d'autres notes) :
- universal/research/digest-2026-W15.md
- universal/research/digest-ai-W16.md
- universal/research/digest-cloud-W16.md
- universal/research/digest-ecommerce-W16.md
- universal/research/digest-iot-W16.md
- universal/mcp-vscode-dedicated-file.md
- universal/anti-bug-set-e-jq-missing-file.md
- universal/anti-bug-zip-executable-bit-lost.md
- universal/concept-context-preservation-after-mitosis.md
- projects/gpparts/anti-bug-checkout-race-condition.md
- projects/second-brain/anti-bug-claude-jsonl-schema.md
- projects/second-brain/anti-bug-grep-confidentiel-faux-positif.md
- projects/second-brain/architecture-paper-synthesizer.md
- projects/second-brain/future-mcp-obsidian-server.md
- projects/second-brain/meta-purpose-lab-for-enterprise.md

_Toutes creees < 30j -- pas de marquage archive-candidate._

### Wikilinks casses 2026-04-14
7 liens casses detectes -- tous presents dans `_meta/lint-ignore.txt` (faux positifs documentes) :
- `[[ancienne-note]]`, `[[note-dependante]]`, `[[note-opposee]]`, `[[wikilinks]]` (exemples template dans decision-knowledge-graph-deferred.md)
- `[[note]]`, `[[note|alias]]` (exemple dans concept-context-preservation-after-mitosis.md)
- `[[wiki]]` (exemple dans future-mcp-obsidian-server.md)

Aucune action requise.

### Candidats archivage 2026-04-14
Vault < 90j -- aucun candidat eligible. `_meta/signals.md` vide (aucun hit/miss enregistre).

### Contradictions potentielles 2026-04-14
Aucune contradiction detectee sur les 67 notes actives.

### Review queue 2026-04-14
`_inbox/review/weekly-review-W16.md` cree avec 3 fleeting les plus anciennes (2026-04-12) :
- anti-bug-mcp-server-scoped-vscode-only
- anti-bug-set-e-jq-missing-file
- anti-bug-zip-executable-bit-lost

## Lint 2026-04-15 — Fleeting guard actif (37 ≥ 15)

**Run mode:** lint seul (synthèse suspendue — fleeting_count=37)

### 4a — Auto-corrections
- Aucune correction appliquée (broken-links.txt vide, toutes notes ont ## Liens)

### 4b — Orphelines
16 notes sans mention dans ## Liens d'autres notes — aucune > 30j, pas de marquage archive-candidate.
- universal/anti-bug-set-e-jq-missing-file.md (3j)
- universal/anti-bug-zip-executable-bit-lost.md (3j)
- universal/concept-cognitive-mitosis-atomicity.md (3j)
- universal/concept-context-preservation-after-mitosis.md (3j)
- projects/second-brain/architecture-paper-synthesizer.md (2j)
- projects/second-brain/future-mcp-obsidian-server.md (2j)
- projects/second-brain/meta-purpose-lab-for-enterprise.md (1j)
- universal/research/digest-ai-W16.md (1j)
- universal/research/digest-cloud-W16.md (1j)
- universal/research/digest-ecommerce-W16.md (1j)
- universal/research/digest-iot-W16.md (1j)
- projects/gpparts/anti-bug-checkout-race-condition.md (date inconnue)
- projects/second-brain/anti-bug-claude-jsonl-schema.md (date inconnue)
- projects/second-brain/anti-bug-grep-confidentiel-faux-positif.md (date inconnue)
- universal/mcp-vscode-dedicated-file.md (date inconnue)
- universal/research/digest-2026-W15.md (date inconnue)

### 4c — Wikilinks cassés
Aucun (broken-links.txt vide).

### 4d — Candidats archivage (0 hit 90j)
Aucun — vault < 30j, fenêtre 90j non atteinte.

### 4e — Contradictions potentielles
Aucune identifiée automatiquement. Vérification manuelle recommandée : #decision (8 notes), #architecture (13 notes).

### 4f — Review queue
weekly-review-W16.md déjà présent avec les 3 notes les plus anciennes :
- [[anti-bug-mcp-server-scoped-vscode-only]] — créée 2026-04-12
- [[anti-bug-set-e-jq-missing-file]] — créée 2026-04-12
- [[anti-bug-zip-executable-bit-lost]] — créée 2026-04-12

