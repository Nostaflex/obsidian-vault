# Anti-bug — Claude CLI auth inaccessible depuis launchd (Keychain Lock)

Source: _inbox/session/session-2026-04-10-weekly.md | Vérifié: 2026-04-11 | Confiance: haute
Tags: #second-brain #anti-bug #launchd #keychain #claude-cli #auth

## Essentiel
Les credentials Claude (OAuth via claude.ai/Max) sont dans `login.keychain-db`, verrouillé hors session utilisateur interactive. En launchd standard, `claude auth status` retourne `loggedIn: false`. Variables env `CLAUDE_ACCESS_TOKEN` et `ANTHROPIC_SESSION_TOKEN` n'overrident pas l'auth Keychain.

## Détail
- Keychain entry : service "Claude Code-credentials", account = username macOS
- Contient : `claudeAiOauth` token + `organizationUuid`
- `claude setup-token` requiert TTY interactif — échoue en bash non-interactif
- `env -i` fonctionne seulement si keychain déjà déverrouillé

**FIX** : `LimitLoadToSessionType Aqua` dans le plist maintient la session utilisateur → keychain accessible → auth réussit.

Tech debt documenté : `docs/tech-debt/launchd-keychain-auth.md`

## Liens
- [[anti-bug-launchd-icloud-tcc]]

<!-- generated: 2026-04-11 -->
