# Pattern — Double Protection iCloud pour _work.nosync/

Source: _inbox/session/session-2026-04-10.md | Vérifié: 2026-04-11 | Confiance: haute
Tags: #second-brain #privacy #icloud #macos #work-nosync #security

## Essentiel
Double protection empêchant la sync iCloud des données sensibles : naming `.nosync` (iCloud ignore nativement) + `xattr` com.apple.fileprovider.ignore#P. Vérification via `brctl status`.

## Détail
**Commandes setup :**
```bash
xattr -w com.apple.fileprovider.ignore#P 1 ~/Documents/Obsidian/KnowledgeBase/_work.nosync/
```

**Vérifications :**
```bash
brctl status ~/Documents/Obsidian/KnowledgeBase/_work.nosync/
# → "Client zone not found" (pas de sync) ✓

xattr -l ~/Documents/Obsidian/KnowledgeBase/_work.nosync/
# → com.apple.fileprovider.ignore#P: 1 ✓
```

integrity-check.sh inclut une alerte si `brctl status` détecte un upload en cours.

**Anti-bug rsync** : lors d'une restauration après crash, rsync doit exclure `_work.nosync/` et `sensitive.nosync/` pour ne pas écraser les données locales avec le backup.

## Liens
- [[architecture-dual-profile-vscode]]
- [[guardrail-nightly-prompt]]

<!-- generated: 2026-04-11 -->
