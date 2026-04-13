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
- Parse la table compacte de `moc-index.md` (colonnes `MOC | tags | n | use_when`)
- Match `$ARGUMENTS` :
  1. **Tag exact** : un mot du topic apparaît dans la colonne `tags` d'un MOC → charger ce MOC
  2. **Match sémantique use_when** : sinon, sélectionner le MOC dont `use_when` colle le mieux au topic
  3. **Multi-MOC** : si 2 MOCs matchent (tags + use_when croisés) → charger les 2
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
