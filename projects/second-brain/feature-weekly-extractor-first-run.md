---
type: discovery
maturity: fleeting
tier: A
created: 2026-04-12
source_chain:
  - "origin: _inbox/session/session-2026-04-11-weekly.md"
  - "via: claude-mem obs #519–#522"
---

# Le weekly extractor est opérationnel — 45 concepts extraits au premier run (PR#4)

Tags: #second-brain #weekly-extractor #claude-mem #feature #pipeline

## Essentiel
Le weekly extractor (`scripts/weekly-extractor.sh` + prompt Claude) a réalisé son premier run complet : 350+ observations traitées, 45 concepts retenus, 14 filtrés par les règles privacy. Pipeline intégré sur main via PR#4.

## Détail
Architecture du weekly extractor : un script bash (`weekly-extractor.sh`) lit le state file `_logs/conversations-processed.json` pour reprendre où le dernier run s'est arrêté (ID haut watermark). Il interroge claude-mem par projet (second-brain, gpparts), applique un filtre de confidentialité qui exclut tout ce qui touche à `_work.nosync` et `sensitive.nosync`, puis écrit une note de synthèse dans `_inbox/session/`. Le state file est mis à jour avec `last_processed_id` pour éviter les doublons aux runs suivants. First run : IDs #1–#514 traités, 45 concepts extraits sur 350+, 14 éliminés pour privacy.

## Liens
- [[decision-weekly-extractor-approach-c]] — décision architecturale qui a conduit à cet implémentation (session interactive)
- [[discovery-mcp-tools-print-mode]] — contrainte MCP en --print qui justifie le mode session interactive pour ce pipeline
- [[discovery-claude-mem-architecture]] — couche claude-mem requêtée par le weekly extractor

<!-- generated: 2026-04-12 -->
