# INDEX — Knowledge Base
Updated: 2026-04-12T12:38:00Z | Active: 38 notes | Ceiling: 300

## Par projet

### universal (10)
- [Convention — MCP VSCode : Fichier mcp.json Dédié](universal/mcp-vscode-dedicated-file.md) — MCP server config appartient à mcp.json, pas settings
- [Pattern — Subagent-Driven Development pour Implémentations Multi-Fichiers](universal/pattern-subagent-driven-development.md) — agents parallèles pour implémentations complexes multi-fichiers
- [Convention — Prix stockés en centimes entiers](universal/prix-centimes-convention.md) — prix en centimes évite les erreurs de virgule flottante
- [TVA Guadeloupe — Taux 8.5% (DOM-TOM)](universal/vat-guadeloupe-8-5.md) — taux TVA DOM-TOM différent du taux continental
- [Research Digest — 2026-W15](universal/research/digest-2026-W15.md) — synthèse hebdomadaire papers arXiv semaine 15
- [Anti-bug — ZIP perd le bit exécutable si chmod +x absent avant archivage](universal/anti-bug-zip-executable-bit-lost.md) — chmod +x doit précéder zip -r sinon scripts non exécutables
- [Anti-bug — set -euo pipefail + jq sur fichier absent crashe avant toute logique init](universal/anti-bug-set-e-jq-missing-file.md) — tester existence fichier avant jq sous set -e
- [La Collector's Fallacy transforme l'accumulation en substitut de compréhension](universal/concept-collectors-fallacy-accumulation-passive.md) — accumuler ≠ comprendre, mesurer le taux d'assimilation
- [La mitose cognitive produit N notes indépendantes depuis 1 source multi-concepts](universal/concept-cognitive-mitosis-atomicity.md) — test fonction pure : note compréhensible sans ses sœurs
- [La section ## Liens annotée préserve le contexte après mitose cognitive](universal/concept-context-preservation-after-mitosis.md) — lien nu = contexte perdu, annotation encode le pont sémantique

### projects/gpparts (4)
- [Anti-bug — Race condition checkout GP Parts](projects/gpparts/anti-bug-checkout-race-condition.md) — race condition commande côté React corrigée
- [Découverte — Facture Électronique FR : Réception obligatoire au 1er septembre 2026](projects/gpparts/discovery-facture-electronique-fr-2026.md) — deadline légale facture electronique France 2026
- [Découverte — Next.js 16 : Breaking Changes à Planifier pour GP Parts](projects/gpparts/discovery-nextjs-16-breaking-changes.md) — migration Next.js 16 à anticiper pour GP Parts
- [Next.js 15 — Breaking Changes : Cache Fetch et Async Headers](projects/gpparts/nextjs-15-breaking-changes-cache.md) — cache fetch no-store par défaut en Next.js 15

### projects/second-brain (24)
- [Anti-bug — Claude CLI auth inaccessible depuis launchd (Keychain Lock)](projects/second-brain/anti-bug-claude-cli-keychain-launchd.md) — session Aqua requise pour keychain depuis launchd
- [Anti-bug — Claude JSONL Conversation History : Schéma Réel](projects/second-brain/anti-bug-claude-jsonl-schema.md) — schéma JSONL claude différent de la doc officielle
- [Anti-bug — grep "confidentiel" génère un faux positif sur les titres H1](projects/second-brain/anti-bug-grep-confidentiel-faux-positif.md) — grep sur mot clé dans titre H1 donne faux positif
- [Anti-bug — launchd bloqué par TCC pour iCloud Drive](projects/second-brain/anti-bug-launchd-icloud-tcc.md) — LimitLoadToSessionType Aqua résout le blocage TCC
- [Anti-bug — MCP server scopé VS Code uniquement, invisible aux scripts launchd](projects/second-brain/anti-bug-mcp-server-scoped-vscode-only.md) — MCP dans settings.json = VS Code seulement, pas global
- [Architecture — Dual Profil VSCode : Personal / Work](projects/second-brain/architecture-dual-profile-vscode.md) — séparation profils VSCode pour privacy employeur
- [Convention — LOG.md Append-Only Anti-Re-Ingestion](projects/second-brain/convention-log-anti-re-ingestion.md) — LOG.md ne jamais effacer, empêche double-ingestion
- [Décision — Architecture Hybride Second Brain (Algo + LLM)](projects/second-brain/decision-architecture-hybride-second-brain.md) — algo pour structure, LLM pour sémantique
- [Knowledge Graph — Route différée (Second Brain)](projects/second-brain/decision-knowledge-graph-deferred.md) — knowledge graph Karpathy différé, pas prioritaire
- [Guanateck distribue le Second Brain Kit en vente unique Gumroad — pas de SaaS](projects/second-brain/decision-mind-free-kit-first-strategy.md) — kit autodéployé, zéro infrastructure, anonymat employeur
- [Décision — Pattern Vault Seed / Runtime](projects/second-brain/decision-vault-seed-runtime-pattern.md) — seed versionné séparé du runtime utilisateur
- [Décision — Weekly Extractor : Approach C (session interactive)](projects/second-brain/decision-weekly-extractor-approach-c.md) — session interactive requise pour accès MCP claude-mem
- [Découverte — Architecture Interne claude-mem](projects/second-brain/discovery-claude-mem-architecture.md) — ChromaDB + SQLite + HTTP worker local, zero cloud
- [Découverte — claude-mem : Risque Privacy (observations non compartimentées)](projects/second-brain/discovery-claude-mem-privacy-risk.md) — observations claude-mem traversent projets sans isolation
- [Découverte — MCP Tools inaccessibles en mode --print](projects/second-brain/discovery-mcp-tools-print-mode.md) — claude --print n'initialise pas MCP, bloque claude-mem
- [Découverte — Nightly Agent : Architecture et Workflow Complet](projects/second-brain/discovery-nightly-agent-architecture.md) — pipeline 6 étapes, launchd 2h17, budget 35k tokens
- [Découverte — Nightly Agent : Contenu Vault Transit vers API Anthropic](projects/second-brain/discovery-nightly-vault-api-transit.md) — contenu vault transite vers Anthropic à chaque run
- [Second Brain v4 — 5 Gaps Karpathy Audit Corrigés](projects/second-brain/discovery-second-brain-v4-gaps-fixes.md) — 5 gaps audit Karpathy corrigés en v4
- [Découverte — Audit Vault : 4 Failles Structurelles Identifiées](projects/second-brain/discovery-vault-failles-audit.md) — 4 failles structurelles audit v4
- [L'Approche B enrichit le vault via watchlist + corpus sans scraping externe](projects/second-brain/feature-enrichment-pipeline-approach-b.md) — enrichissement ciblé depuis watchlist, 7 tasks PR#5
- [Le weekly extractor est opérationnel — 45 concepts extraits au premier run](projects/second-brain/feature-weekly-extractor-first-run.md) — PR#4 mergé, 350+ obs traitées, 14 filtrées privacy
- [Guardrail — Règle Non-Annulable Nightly Prompt](projects/second-brain/guardrail-nightly-prompt.md) — règles absolues nightly prompt non annulables
- [Pattern — Double Protection iCloud pour _work.nosync/](projects/second-brain/icloud-work-nosync-protection.md) — double protection iCloud + gitignore pour données sensibles
- [Pattern — _inbox/raw/ Input Layer (Karpathy Raw Input Zone)](projects/second-brain/pattern-inbox-raw-layer.md) — zone entrée raw découplée du vault compilé

## Par type

### anti-bug (8)
- [Anti-bug — Race condition checkout GP Parts](projects/gpparts/anti-bug-checkout-race-condition.md) — race condition commande côté React corrigée
- [Anti-bug — Claude CLI auth inaccessible depuis launchd](projects/second-brain/anti-bug-claude-cli-keychain-launchd.md) — session Aqua requise pour keychain depuis launchd
- [Anti-bug — Claude JSONL Conversation History : Schéma Réel](projects/second-brain/anti-bug-claude-jsonl-schema.md) — schéma JSONL claude différent de la doc officielle
- [Anti-bug — grep "confidentiel" génère un faux positif sur les titres H1](projects/second-brain/anti-bug-grep-confidentiel-faux-positif.md) — grep sur mot clé dans titre H1 donne faux positif
- [Anti-bug — launchd bloqué par TCC pour iCloud Drive](projects/second-brain/anti-bug-launchd-icloud-tcc.md) — LimitLoadToSessionType Aqua résout le blocage TCC
- [Anti-bug — MCP server scopé VS Code uniquement, invisible aux scripts launchd](projects/second-brain/anti-bug-mcp-server-scoped-vscode-only.md) — MCP dans settings.json = VS Code seulement, pas global
- [Anti-bug — ZIP perd le bit exécutable si chmod +x absent avant archivage](universal/anti-bug-zip-executable-bit-lost.md) — chmod +x doit précéder zip -r sinon scripts non exécutables
- [Anti-bug — set -euo pipefail + jq sur fichier absent crashe avant toute logique init](universal/anti-bug-set-e-jq-missing-file.md) — tester existence fichier avant jq sous set -e

### decisions (6)
- [Décision — Architecture Hybride Second Brain (Algo + LLM)](projects/second-brain/decision-architecture-hybride-second-brain.md) — algo pour structure, LLM pour sémantique
- [Knowledge Graph — Route différée (Second Brain)](projects/second-brain/decision-knowledge-graph-deferred.md) — knowledge graph Karpathy différé, pas prioritaire
- [Guanateck distribue le Second Brain Kit en vente unique Gumroad — pas de SaaS](projects/second-brain/decision-mind-free-kit-first-strategy.md) — kit autodéployé, zéro infrastructure, anonymat employeur
- [Décision — Pattern Vault Seed / Runtime](projects/second-brain/decision-vault-seed-runtime-pattern.md) — seed versionné séparé du runtime utilisateur
- [Décision — Weekly Extractor : Approach C (session interactive)](projects/second-brain/decision-weekly-extractor-approach-c.md) — session interactive requise pour accès MCP claude-mem
- [L'Approche B enrichit le vault via watchlist + corpus sans scraping externe](projects/second-brain/feature-enrichment-pipeline-approach-b.md) — enrichissement ciblé depuis watchlist, 7 tasks PR#5

### patterns (4)
- [Convention — MCP VSCode : Fichier mcp.json Dédié](universal/mcp-vscode-dedicated-file.md) — MCP server config appartient à mcp.json, pas settings
- [Pattern — Subagent-Driven Development pour Implémentations Multi-Fichiers](universal/pattern-subagent-driven-development.md) — agents parallèles pour implémentations complexes multi-fichiers
- [Guardrail — Règle Non-Annulable Nightly Prompt](projects/second-brain/guardrail-nightly-prompt.md) — règles absolues nightly prompt non annulables
- [Pattern — _inbox/raw/ Input Layer (Karpathy Raw Input Zone)](projects/second-brain/pattern-inbox-raw-layer.md) — zone entrée raw découplée du vault compilé

### discoveries (9)
- [Découverte — Architecture Interne claude-mem](projects/second-brain/discovery-claude-mem-architecture.md) — ChromaDB + SQLite + HTTP worker local, zero cloud
- [Découverte — claude-mem : Risque Privacy](projects/second-brain/discovery-claude-mem-privacy-risk.md) — observations claude-mem traversent projets sans isolation
- [Découverte — MCP Tools inaccessibles en mode --print](projects/second-brain/discovery-mcp-tools-print-mode.md) — claude --print n'initialise pas MCP, bloque claude-mem
- [Découverte — Nightly Agent : Architecture et Workflow Complet](projects/second-brain/discovery-nightly-agent-architecture.md) — pipeline 6 étapes, launchd 2h17, budget 35k tokens
- [Découverte — Nightly Agent : Contenu Vault Transit vers API Anthropic](projects/second-brain/discovery-nightly-vault-api-transit.md) — contenu vault transite vers Anthropic à chaque run
- [Second Brain v4 — 5 Gaps Karpathy Audit Corrigés](projects/second-brain/discovery-second-brain-v4-gaps-fixes.md) — 5 gaps audit Karpathy corrigés en v4
- [Découverte — Audit Vault : 4 Failles Structurelles Identifiées](projects/second-brain/discovery-vault-failles-audit.md) — 4 failles structurelles audit v4
- [Découverte — Facture Électronique FR : Réception obligatoire au 1er septembre 2026](projects/gpparts/discovery-facture-electronique-fr-2026.md) — deadline légale facture electronique France 2026
- [Découverte — Next.js 16 : Breaking Changes à Planifier pour GP Parts](projects/gpparts/discovery-nextjs-16-breaking-changes.md) — migration Next.js 16 à anticiper pour GP Parts

### concept (3)
- [La Collector's Fallacy transforme l'accumulation en substitut de compréhension](universal/concept-collectors-fallacy-accumulation-passive.md) — accumuler ≠ comprendre, mesurer le taux d'assimilation
- [La mitose cognitive produit N notes indépendantes depuis 1 source multi-concepts](universal/concept-cognitive-mitosis-atomicity.md) — test fonction pure : note compréhensible sans ses sœurs
- [La section ## Liens annotée préserve le contexte après mitose cognitive](universal/concept-context-preservation-after-mitosis.md) — lien nu = contexte perdu, annotation encode le pont sémantique

### bridge (0)
_(aucune note bridge active)_
