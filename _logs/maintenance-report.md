# Maintenance Report — Knowledge Base

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
