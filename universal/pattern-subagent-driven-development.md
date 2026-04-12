# Pattern — Subagent-Driven Development pour Implémentations Multi-Fichiers

Source: _inbox/session/session-2026-04-10-second-brain-v2.md | Vérifié: 2026-04-11 | Confiance: haute
Tags: #pattern #claude-code #subagent #development #quality #review

## Essentiel
Pour les implémentations multi-fichiers complexes : 1 subagent par tâche indépendante + spec reviewer + code quality reviewer. Pattern validé : les reviewers ont trouvé 3 défauts réels dans `weekly-extractor.sh` (mkdir _logs, CLAUDE_BIN, PIPESTATUS).

## Détail
**Structure du pattern** :
1. Décomposer l'implémentation en tâches indépendantes
2. Un subagent par tâche (parallélisable)
3. Spec reviewer : vérifie conformité aux requirements
4. Code quality reviewer : détecte les défauts techniques

**Défauts réels trouvés par les reviewers sur weekly-extractor.sh** :
- `mkdir _logs` manquant avant écriture du log
- `CLAUDE_BIN` non défini → fallback `which claude` nécessaire
- `PIPESTATUS` non capturé → erreur pipeline silencieuse

**Quand l'utiliser** : tout script/feature > 50 lignes touchant plusieurs fichiers.

## Liens

<!-- generated: 2026-04-11 -->
