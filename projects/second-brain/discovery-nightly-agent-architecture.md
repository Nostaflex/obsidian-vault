# Découverte — Nightly Agent : Architecture et Workflow Complet

Source: _inbox/session/session-2026-04-10-weekly.md | Vérifié: 2026-04-11 | Confiance: haute
Tags: #second-brain #discovery #nightly-agent #launchd #architecture #workflow

## Essentiel
launchd cron à 2h17 → `nightly-agent.sh` → `claude --print .nightly-prompt.md` → notes dans `_inbox/agent/YYYY-MM-DD/`. Budget Light Mode, sans WebSearch, 0 coût extra.

## Détail
- Script : `~/Documents/Obsidian/KnowledgeBase/nightly-agent.sh`
- Prompt : `.nightly-prompt.md` (versionné dans repo seed `vault/`)
- Output : `_inbox/agent/YYYY-MM-DD/` uniquement (zone safe)
- Logs : `_logs/nightly-agent.log`
- État : `_logs/last-nightly.json`
- Test manuel : `launchctl start com.second-brain.nightly`

**integrity-check.sh** : exécuté AVANT chaque run (coût 0 token) :
1. Téléchargement forcé iCloud (`brctl download`)
2. Backup atomique vers `~/.second-brain-backup/` (hors iCloud)
3. Détection crash run précédent (status "in_progress") → restore depuis backup
4. Détection copies de conflit iCloud
5. Reconstruction INDEX.md depuis fichiers réels
6. Vérification wikilinks cassés

## Liens
- [[anti-bug-launchd-icloud-tcc]] — bug TCC launchd qui bloquait l'accès iCloud depuis ce script
- [[discovery-mcp-tools-print-mode]] — contrainte --print qui empêche MCP dans le nightly agent
- [[decision-vault-seed-runtime-pattern]] — pattern architectural qui structure le déploiement du vault
- [[discovery-second-brain-v4-gaps-fixes]] — gaps Karpathy corrigés dont cette architecture est la réponse
- [[pattern-inbox-raw-layer]] — couche d'entrée que le nightly agent traite à l'Étape 2
- [[convention-log-anti-re-ingestion]] — LOG.md append-only géré par ce même agent
- [[feature-weekly-extractor-first-run]] — composant hebdomadaire complémentaire, opérationnel depuis PR#4
- [[feature-enrichment-pipeline-approach-b]] — pipeline d'enrichissement Approche B, mergé PR#5

<!-- generated: 2026-04-11 -->
