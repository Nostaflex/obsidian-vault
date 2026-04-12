# Anti-bug — Claude JSONL Conversation History : Schéma Réel

Source: _inbox/session/session-2026-04-10-weekly.md | Vérifié: 2026-04-11 | Confiance: haute
Tags: #second-brain #anti-bug #claude-cli #jsonl #conversation-history #schema

## Essentiel
Les conversations Claude sont dans `~/.claude/projects/` avec répertoires path-encodés. **Anti-bug critique** : le contenu des messages est dans `d['message']['content']`, **pas** dans `d['content']`. Certains fichiers JSONL ne contiennent que des "queue operations" sans messages texte.

## Détail
Structure réelle :
```python
d['message']['content']  # CORRECT
d['content']             # FAUX — KeyError ou données incorrectes
```

Types de fichiers JSONL :
1. Queue operations — pas de messages texte (filtrer)
2. Fichiers conversation — `type=message`, `operation=assistant/user`

Pertinent pour tout projet d'extraction de l'historique Claude vers le vault ou claude-mem.

## Liens
- [[decision-weekly-extractor-approach-c]]
- [[discovery-claude-mem-architecture]]

<!-- generated: 2026-04-11 -->
