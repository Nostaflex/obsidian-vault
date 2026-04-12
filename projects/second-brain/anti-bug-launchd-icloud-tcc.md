# Anti-bug — launchd bloqué par TCC pour iCloud Drive

Source: _inbox/session/session-2026-04-10-weekly.md | Vérifié: 2026-04-11 | Confiance: haute
Tags: #second-brain #anti-bug #launchd #icloud #macos #tcc

## Essentiel
macOS bloque l'accès de launchd à iCloud Drive via TCC. `SessionCreate=true` dans le plist ne résout pas ce problème. **FIX confirmé** : `LimitLoadToSessionType Aqua` dans le plist — donne accès au login keychain et à iCloud.

## Détail
Investigation complète menée le 2026-04-10 :
- Launcher proxy hors iCloud → échoué
- Full Disk Access grant → insuffisant
- `SessionCreate=true` → "Operation not permitted" persiste
- **FIX FINAL** : remplacer `SessionCreate` par `LimitLoadToSessionType Aqua`

Fichier : `~/Library/LaunchAgents/com.second-brain.nightly.plist`
Effet secondaire positif : résout aussi l'accès au keychain (Claude CLI auth).

## Liens
- [[anti-bug-claude-cli-keychain-launchd]]

<!-- generated: 2026-04-11 -->
