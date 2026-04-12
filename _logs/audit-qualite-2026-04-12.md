# Audit Qualité — KnowledgeBase v5 — 2026-04-12

Auditeur : Claude Sonnet 4.6  
Heure : 2026-04-12T14:22 GMT+2  
Fichiers lus : corpus_collector.py, paper_synthesizer.py, integrity-check.sh, .nightly-prompt.md, VAULT.md, _meta/notebooklm-context-ai.md, _meta/notebooklm-context-cloud.md, _logs/last-nightly.json, _logs/broken-links.txt

---

## corpus_collector.py

✅ **Imports** — Tous les 12 imports sont utilisés : `math` (log dans compute_relevance_score L135), `subprocess` (rebuild corpus L460), tous les autres clairement utilisés.

✅ **Type hints** — `normalize_arxiv_id(arxiv_id: str) -> str`, `compute_relevance_score(paper: dict, vault_tags: list, domain: str) -> float`, `score_to_tier(score: float) -> str` — cohérents et complets.

✅ **Chemin seen-arxiv-ids.txt** — `SEEN_IDS_FILE = VAULT / "_logs/seen-arxiv-ids.txt"` (L33) — cohérent avec la structure du vault.

✅ **Format frontmatter YAML** — Champs `relevance_score`, `tier`, `citation_count`, `keywords` présents dans `format_paper_as_markdown()`. Compatible avec `parse_frontmatter()` de paper_synthesizer.py (lecture par clé `domain`, `arxiv_id`, `source_url`).

✅ **Compatibilité rétrograde** — Les anciens papers sans nouveaux champs : `parse_frontmatter()` utilise `.get()` avec fallback — pas de crash si champs absents.

✅ **Fallback DOMAIN_FALLBACK_KEYWORDS** — Cohérent : 4 domaines (ai, iot, cloud, ecommerce) correspondent exactement aux clés de `DOMAINS`. Fallback activé si `vault_tags` vide (INDEX.md absent).

---

## paper_synthesizer.py

✅ **Zéro référence Anthropic** — Aucun résidu `anthropic`, `ANTHROPIC_API_KEY`, `claude-haiku`, `batches`, `messages.batches`. Confirmé par grep.

✅ **Import google.generativeai** — `import google.generativeai as genai` (L31) — correct.

✅ **Cohérence des chemins** :
- Input papers : `_inbox/raw/papers/{domain}/` ✅ correspond à `RAW_DIR` de corpus_collector.py
- Output concepts : `_inbox/raw/concepts/draft-{slug}.md` ✅ dossier créé par `CONCEPTS_DIR.mkdir(parents=True, exist_ok=True)` (L219)
- Output digests : `universal/research/digest-{domain}-W{N}.md` ✅ cohérent avec `.nightly-prompt.md` (Étape 2A référence `_inbox/raw/concepts/`)
- Processed papers : `_inbox/raw/papers/{domain}/_processed/` ✅ séparé de `_inbox/raw/_processed/` de l'agent

✅ **Format frontmatter output draft-*.md** — Champs présents : `type: concept`, `maturity: fleeting`, `tier`, `created`, `source_chain` (2 entrées origin + via). Cohérent avec le template `.nightly-prompt.md`.

✅ **Champ notebooklm_meta absent** — Aucun champ `notebooklm_meta` dans les outputs de paper_synthesizer.py. Correct.

✅ **Rate limiting** — `GEMINI_RATE_LIMIT_DELAY = 4.0` appliqué avec `if i < len(papers) - 1: time.sleep(...)` (L400-401) — le délai est bien sauté après le dernier paper.

✅ **Gestion API key manquante** — Message d'erreur pointe vers `https://aistudio.google.com/apikey` (L535).

✅ **Slugification** — `slugify()` (L177-189) gère les accents fr (àáâ→a, èéê→e, ìíî→i, òóô→o, ùúû→u, ç→c), puis supprime tous les caractères non alphanum, collapse les espaces en tirets. Robuste pour les titres français.

✅ **estimated_cost_usd** — Toujours `0.0` (L485) — correct et documenté : Gemini free tier, pas de coût réel.

⚠️ **CORRIGÉ — maturity digest** — `write_digest()` produisait `maturity: literature` au lieu de `maturity: fleeting`. Selon VAULT.md, `literature` = "Validé par Djemil" — or les digests Gemini ne sont pas validés. **Corrigé** : `maturity: literature` → `maturity: fleeting` (L279).

---

## integrity-check.sh

✅ **Fix basename** — Le code utilise bien `BASENAME="${LINK##*/}"` (L114) avant le `find`. Pattern correct pour extraire le basename Obsidian.

✅ **Exclusion sensitive.nosync et _work.nosync** — Le `grep -r` source scan couvre `$VAULT/universal` et `$VAULT/projects` seulement — sensitive.nosync et _work.nosync sont naturellement hors scope.

⚠️ **CORRIGÉ — Exclusion _processed/ et _archive/ dans INDEX** — Le `find` pour INDEX.md comptait les fichiers dans `_processed/` et `_archive/` si jamais ces dossiers se trouvaient dans `universal/` ou `projects/`. **Corrigé** : ajout de `! -path "*/_processed/*" ! -path "*/_archive/*"` sur les deux `find` de la section INDEX (L61-85).

✅ **_archive/ hors scope orphan check** — Le check des orphelines (Étape 4b nightly) opère sur `_meta/LOG.md` et backlinks — les notes dans `_archive/` n'ont pas vocation à être liées. Le scan de broken-links (L105-120) couvre `universal/` et `projects/` seulement — les notes archivées ne sont pas scannées comme source. Comportement correct.

✅ **Dossiers _inbox/raw/concepts/ et _inbox/review/** — L'integrity-check n'a pas vocation à scanner `_inbox/` (notes en transit). L'INDEX.md ne liste que les notes permanentes (`universal/` et `projects/`). Comportement correct — pas de modification nécessaire.

---

## .nightly-prompt.md

✅ **_inbox/raw/concepts/** — Mentionné explicitement à l'Étape 2A (L142-153). Correct.

✅ **_inbox/review/** — Mentionné pour les bridge notes (Étape 3, L191-194) et weekly review (Étape 4f, L248). Correct.

✅ **_meta/lint-ignore.txt** — Mentionné à l'Étape 4 (L202). Fichier confirmé existant dans `_meta/`.

✅ **_meta/notebooklm-context-global.md** — Mentionné à l'Étape 5 (L305). Fichier confirmé existant dans `_meta/`.

✅ **Budget 20k tokens Steps 1-3** — Documenté avec raison explicite (L23) : "réduit de 40k à 20k car paper_synthesizer.py pré-synthétise les concepts avant ingest". Correct.

⚠️ **CORRIGÉ (last-nightly.json) — last_lint_date manquant** — Le champ `last_lint_date` est lu à l'Étape 0 (L94) et écrit à l'Étape 6 (L337), mais il était absent du fichier `_logs/last-nightly.json` actuel. La guard condition de l'Étape 0 (`lint effectué il y a moins de 3 jours`) ne pouvait jamais déclencher le skip. **Corrigé** : champ ajouté dans `_logs/last-nightly.json` avec valeur `"2026-04-12T01:51:11Z"` (= last_run du run précédent).

---

## Cohérence frontmatter entre composants

| Champ | Template .nightly-prompt.md | paper_synthesizer.py (concept) | paper_synthesizer.py (digest) | VAULT.md |
|-------|----------------------------|-------------------------------|------------------------------|---------|
| `type` | concept\|decision\|pattern\|discovery\|anti-bug\|bridge\|literature | `concept` ✅ | `literature` ✅ | même liste ✅ |
| `maturity` | fleeting (agent) | `fleeting` ✅ | `fleeting` ✅ (après correction) | fleeting\|literature\|evergreen\|archive-candidate ✅ |
| `tier` | S\|A\|B | S\|A\|B (depuis LLM) ✅ | `A` (fixe) ✅ | S\|A\|B ✅ |
| `created` | YYYY-MM-DD | `date.today().isoformat()` ✅ | `date.today().isoformat()` ✅ | YYYY-MM-DD ✅ |
| `source_chain` | liste de strings origin/via | 2 entrées : origin URL + via synthesizer ✅ | 2 entrées : origin arXiv W{N} + via synthesizer ✅ | liste de strings ✅ |

**Résultat** : après la correction `maturity: literature → fleeting` dans write_digest(), tous les champs sont cohérents entre les 3 composants.

---

## Wikilinks résiduels decisions/

⚠️ **CORRIGÉ — 4 liens [[decisions/...]] dans fichiers _meta/**

Trouvés dans `_meta/notebooklm-context-ai.md` (3 liens) et `_meta/notebooklm-context-cloud.md` (2 liens). Les décisions existent sous `projects/second-brain/decision-*.md` (sans sous-dossier).

| Avant | Après | Fichier |
|-------|-------|---------|
| `[[decisions/architecture-hybride-second-brain]]` | `[[decision-architecture-hybride-second-brain]]` | notebooklm-context-ai.md, notebooklm-context-cloud.md |
| `[[decisions/knowledge-graph-deferred]]` | `[[decision-knowledge-graph-deferred]]` | notebooklm-context-ai.md |
| `[[decisions/weekly-extractor-approach-c]]` | `[[decision-weekly-extractor-approach-c]]` | notebooklm-context-ai.md |
| `[[decisions/vault-seed-runtime-pattern]]` | `[[decision-vault-seed-runtime-pattern]]` | notebooklm-context-cloud.md |

✅ Aucun lien `[[decisions/...]]` dans `projects/` ni `universal/`.  
✅ Références dans `_inbox/session/session-2026-04-11.md` ligne 54 : chemin en backtick (plain text), pas un wikilink — pas de correction nécessaire.

---

## Corrections effectuées

| # | Fichier | Ligne(s) | Avant | Après |
|---|---------|----------|-------|-------|
| 1 | `VAULT.md` | L98 | `Batch API Claude →` | `Gemini API →` |
| 2 | `paper_synthesizer.py` | L279 | `maturity: literature` | `maturity: fleeting` |
| 3 | `integrity-check.sh` | L61-65 | `find` sans exclusion `_processed/` `_archive/` | Ajout `! -path "*/_processed/*" ! -path "*/_archive/*"` |
| 4 | `integrity-check.sh` | L77-81 | `find` sans exclusion `_processed/` `_archive/` | Ajout `! -path "*/_processed/*" ! -path "*/_archive/*"` |
| 5 | `_logs/last-nightly.json` | — | Champ `last_lint_date` absent | Ajout `"last_lint_date": "2026-04-12T01:51:11Z"` |
| 6 | `_meta/notebooklm-context-ai.md` | L12-14 | 3× `[[decisions/...]]` | 3× `[[decision-...]]` |
| 7 | `_meta/notebooklm-context-cloud.md` | L12-13 | 2× `[[decisions/...]]` | 2× `[[decision-...]]` |

---

## Résumé de santé

- **corpus_collector.py** : aucune correction nécessaire — code propre, imports tous utilisés, chemins cohérents.
- **paper_synthesizer.py** : 1 correction (maturity digest fleeting). Zéro résidu Anthropic. Pipeline complet et cohérent.
- **integrity-check.sh** : 1 correction (_processed/_archive exclusion INDEX). Basename fix déjà en place.
- **.nightly-prompt.md** : aucune correction. Budget documenté, guard condition cohérente.
- **Frontmatter** : cohérence totale après correction maturity.
- **Wikilinks decisions/** : 5 liens corrigés dans _meta/. Projects/ et universal/ propres.
- **last-nightly.json** : last_lint_date ajouté, guard condition Step 0 désormais fonctionnelle.

---

## Addendum — Faux positifs lint-ignore.txt

Après re-run d'`integrity-check.sh`, les 4 liens `[[decisions/...]]` ne figurent plus dans `broken-links.txt` (corrigés). Restent 4 faux positifs :

| Lien | Source | Raison |
|------|--------|--------|
| `[[ancienne-note]]` | `decision-knowledge-graph-deferred.md` L48 | Exemple dans code block markdown |
| `[[note-opposée]]` | `decision-knowledge-graph-deferred.md` L49 | Exemple dans code block markdown |
| `[[note-dépendante]]` | `decision-knowledge-graph-deferred.md` L50 | Exemple dans code block markdown |
| `[[wikilinks]]` | `decision-knowledge-graph-deferred.md` L29 | Mot utilisé en prose, pas un lien réel |

**Action :** Ajoutés dans `_meta/lint-ignore.txt` (correction #8). Le nightly agent respecte ce fichier à l'Étape 4.

| 8 | `_meta/lint-ignore.txt` | — | Fichier vide (commentaires seulement) | 4 faux positifs documentés |
