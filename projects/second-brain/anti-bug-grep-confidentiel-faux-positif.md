# Anti-bug — grep "confidentiel" génère un faux positif sur les titres H1

Source: _inbox/session/session-2026-04-10-weekly.md | Vérifié: 2026-04-11 | Confiance: haute
Tags: #second-brain #anti-bug #integrity-check #grep #index #bash

## Essentiel
Dans `integrity-check.sh`, le pattern `grep "confidentiel"` matche le titre H1 d'une section INDEX, pas seulement le body. Génère un faux positif dans la vérification.

## Détail
**Problème** : `grep "confidentiel"` matche les lignes `# Titre confidentiel` dans l'INDEX.

**Fix** : exclure les lignes commençant par `#` :
```bash
grep -v "^#" fichier | grep "confidentiel"
```

Fichier concerné : `scripts/integrity-check.sh` (dans le repo seed `vault/`).

**Rappel** : toute modification de `integrity-check.sh` doit se faire dans `vault/` puis propagée via `setup.sh --update`.

## Liens
- [[decision-vault-seed-runtime-pattern]]
- [[discovery-nightly-agent-architecture]]

<!-- generated: 2026-04-11 -->
