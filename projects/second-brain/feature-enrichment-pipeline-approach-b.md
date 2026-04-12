---
type: decision
maturity: fleeting
tier: A
created: 2026-04-12
source_chain:
  - "origin: _inbox/session/session-2026-04-11-weekly.md"
  - "via: claude-mem obs #606 / #611 / #626 / #630–#633"
---

# L'Approche B enrichit le vault via watchlist + corpus sans scraping web externe (PR#5 mergé)

Tags: #second-brain #enrichment #decision #watchlist #pipeline #architecture

## Essentiel
L'enrichissement du vault suit l'Approche B : le nightly agent consulte `_meta/watchlist.md` et les signaux corpus pour enrichir les notes existantes, sans jamais faire de scraping web autonome. Implémenté en 7 tâches, mergé PR#5, 13 checks e2e validés.

## Détail
Trois approches étaient en compétition : A (web crawling autonome), B (watchlist + corpus interne), C (manuel). L'Approche B a été retenue pour sa fiabilité et son respect des limites de l'agent nocturne. Le pipeline enrichissement lit `_meta/watchlist.md`, requête claude-mem pour des observations récentes pertinentes aux thèmes prioritaires, et enrichit les cross-références des notes vault. Scheduling hebdomadaire via `scripts/com.second-brain.weekly.plist` (launchd, session Aqua). Les 7 tasks du sprint : state file, watchlist reader, corpus requête, enrichissement cross-refs, filtre privacy, plist launchd, validation e2e.

## Liens
- [[decision-architecture-hybride-second-brain]] — décision architecturale cadre dans laquelle s'inscrit ce pipeline
- [[discovery-nightly-agent-architecture]] — agent nocturne qui héberge ce pipeline

<!-- generated: 2026-04-12 -->
