# INDEX — Knowledge Base
Updated: 2026-04-15T00:35:00+02:00 | Active: 67 notes | Ceiling: 300

## Par projet

### universal (24)
- [[A-2604-07760v1-1]] — Fusionner radiateur, panneaux solaires et processeurs dans une structure unique
- [[A-2604-07988v1-1]] — Agents LLM publient actions dans log partagé avant exécution
- [[A-2604-07988v1-2]] — Défaillances agent diagnostiquées par autoanalyse LLM du log
- [[A-2604-08123v1-1]] — Fragmentation pipelines IA en services autonomes = efficacité compute
- [[A-2604-08123v1-2]] — Partage composants stables inter-workflow réduit empreinte mémoire cluster
- [[A-2604-08182v1-1]] — GPU power varie par paliers DVFS, pas linéairement
- [[A-2604-08182v1-2]] — TCO 5 ans dépend autant électricité que matériel
- [[A-2604-08188v1-1]] — Surfaces transmissives intelligentes amplifient capacité spectrale multi-antenne
- [[A-2604-08188v1-2]] — Contrainte énergétique restructure design surfaces RIS
- [[A-2604-08197v1-1]] — Diffusion discrète génère candidats faisceau mmWave efficacement
- [[A-2604-08197v1-2]] — Gestion faisceau sondage limité = MDP alignement mmWave
- [[A-2604-08199v1-1]] — Modèles de monde capturent interactions trafic mobile / paramètres réseau
- [[A-2604-08199v1-2]] — Fusion image-séquence multimodale renforce représentation spatiale
- [[anti-bug-set-e-jq-missing-file]] — set -euo pipefail + jq fichier absent = exit silencieux
- [[anti-bug-zip-executable-bit-lost]] — ZIP perd bit exécutable si chmod +x non appliqué
- [[concept-cognitive-mitosis-atomicity]] — Mitose cognitive : N notes indépendantes depuis 1 source multi-concepts
- [[concept-collectors-fallacy-accumulation-passive]] — Collector's Fallacy : accumulation ≠ compréhension
- [[concept-context-preservation-after-mitosis]] — ## Liens annoté = mécanisme préservation contexte post-mitose
- [[concept-physics-constraints-eliminate-nocturnal-solar-artifacts]] — Contraintes physiques éliminent artefacts solaires nocturnes dans DL
- [[future-gan-loop-orchestrator]] — GAN Loop orchestrator pour heavy dev — design deferred
- [[mcp-vscode-dedicated-file]] — VSCode refuse MCP dans settings.json — fichier mcp.json dédié requis
- [[pattern-subagent-driven-development]] — Subagent-Driven Development : 1 subagent par tâche indépendante
- [[prix-centimes-convention]] — Tous les prix sont des entiers en centimes, jamais de float
- [[vat-guadeloupe-8-5]] — TVA Guadeloupe (971) : 8.5%, différent du taux métropolitain

### universal/research (5)
- [[digest-2026-W15]] — Research Digest W15
- [[digest-ai-W16]] — Digest AI W16
- [[digest-cloud-W16]] — Digest Cloud W16
- [[digest-ecommerce-W16]] — Digest ecommerce W16
- [[digest-iot-W16]] — Digest IoT W16

### projects/gpparts (6)
- [[A-2604-07767v1-1]] — Contrôle stratégique cloud + autonomie périphérique : architecture hybride edge/cloud
- [[A-2604-07767v1-2]] — Agents périphériques perçoivent UI en continu pour coordination sans serveur
- [[anti-bug-checkout-race-condition]] — setOrderPlaced(true) AVANT clearCart() — inverser cause race condition
- [[discovery-facture-electronique-fr-2026]] — Réception factures électroniques obligatoire en France au 1er sept 2026
- [[discovery-nextjs-16-breaking-changes]] — Breaking changes Next.js 16 identifiés comme points de friction
- [[nextjs-15-breaking-changes-cache]] — Next.js 15 : fetch() no-store par défaut, async headers/cookies

### projects/second-brain (32)
- [[anti-bug-claude-cli-keychain-launchd]] — Credentials Claude dans login.keychain-db — inaccessibles depuis launchd
- [[anti-bug-claude-jsonl-schema]] — Conversations Claude dans ~/.claude/projects/ avec répertoires path-encodés
- [[anti-bug-grep-confidentiel-faux-positif]] — grep "confidentiel" matche titre H1 — faux positif integrity-check.sh
- [[anti-bug-launchd-icloud-tcc]] — macOS bloque launchd iCloud Drive via TCC — Full Disk Access requis
- [[anti-bug-mcp-server-scoped-vscode-only]] — Serveurs MCP settings.json actifs globalement, pas seulement VS Code
- [[architecture-dual-profile-vscode]] — Deux profils VSCode Personal/Work avec LLM et accès vault distincts
- [[architecture-paper-synthesizer]] — paper_synthesizer.py produit extractions atomiques Tier S/A/B
- [[architecture-token-efficient-skills]] — ADR : design token-efficient pour skills custom Claude Code
- [[audit-setup-claude-code-2026-04-13]] — Audit complet setup Claude Code Second Brain 2026-04-13
- [[convention-log-anti-re-ingestion]] — LOG.md append-only empêche re-ingestion des sources déjà traitées
- [[decision-architecture-hybride-second-brain]] — Architecture hybride Algo+LLM choisie : injection directe vault
- [[decision-bash-vs-python-boundary]] — ADR : frontière Bash vs Python dans le pipeline Second Brain
- [[decision-knowledge-graph-deferred]] — Knowledge Graph évalué et différé pour Second Brain
- [[decision-mind-free-kit-first-strategy]] — Guanateck vend Second Brain Kit en vente unique Gumroad
- [[decision-vault-seed-runtime-pattern]] — Repo git contient vault/ source de vérité pour initialisation
- [[decision-weekly-extractor-approach-c]] — Weekly extractor = session Claude interactive (Approach C)
- [[discovery-claude-mem-architecture]] — claude-mem utilise SQLite local dans ~/.claude-mem/ — offline
- [[discovery-claude-mem-privacy-risk]] — Observations claude-mem non compartimentées par zone sensible
- [[discovery-mcp-tools-print-mode]] — MCP Tools inaccessibles en mode --print (non-interactif)
- [[discovery-nightly-agent-architecture]] — launchd → nightly-agent.sh → claude --print → vault
- [[discovery-nightly-vault-api-transit]] — nightly-agent.sh concatène vault et transmet à API Anthropic
- [[discovery-second-brain-v4-gaps-fixes]] — 5 gaps Karpathy audit corrigés dans Second Brain v4
- [[discovery-vault-failles-audit]] — 4 failles structurelles identifiées dans audit vault 2026-04-10
- [[feature-enrichment-pipeline-approach-b]] — Approche B : enrichissement vault via watchlist + corpus sans scraping
- [[feature-weekly-extractor-first-run]] — Weekly extractor opérationnel — 45 concepts extraits au premier run
- [[future-managed-agents-anthropic]] — Managed Agents Anthropic — future implementation deferred
- [[future-mcp-obsidian-server]] — MCP Obsidian Server MarkusPfundstein — future implementation deferred
- [[guardrail-nightly-prompt]] — Guardrail non-annulable nightly prompt pour _work.nosync/
- [[icloud-work-nosync-protection]] — Double protection iCloud pour _work.nosync/ (gitignore + .nosync)
- [[meta-purpose-lab-for-enterprise]] — Second Brain : triple vocation intentionnelle (lab + kit + référence)
- [[pattern-inbox-raw-layer]] — _inbox/raw/ : zone de dépôt Karpathy raw input layer
- [[tech-debt-registry]] — Tech Debt Registry Second Brain Pipeline

## Par type

### concept (19)
- [[A-2604-07760v1-1]] — Fusion thermique/solaire/compute en structure unique
- [[A-2604-07767v1-1]] — Contrôle stratégique cloud + autonomie périphérique
- [[A-2604-07767v1-2]] — Agents périphériques perçoivent UI en continu
- [[A-2604-07988v1-1]] — Agents LLM publient actions dans log partagé avant exécution
- [[A-2604-07988v1-2]] — Défaillances agent diagnostiquées par autoanalyse LLM du log
- [[A-2604-08123v1-1]] — Fragmentation pipelines IA = efficacité compute
- [[A-2604-08123v1-2]] — Partage composants stables inter-workflow réduit mémoire cluster
- [[A-2604-08182v1-1]] — GPU power varie par paliers DVFS, pas linéairement
- [[A-2604-08182v1-2]] — TCO 5 ans dépend autant électricité que matériel
- [[A-2604-08188v1-1]] — Surfaces transmissives amplifient capacité spectrale multi-antenne
- [[A-2604-08188v1-2]] — Contrainte énergétique restructure design surfaces RIS
- [[A-2604-08197v1-1]] — Diffusion discrète génère candidats faisceau mmWave
- [[A-2604-08197v1-2]] — Gestion faisceau = MDP alignement mmWave
- [[A-2604-08199v1-1]] — Modèles de monde : trafic mobile ↔ paramètres réseau
- [[A-2604-08199v1-2]] — Fusion image-séquence multimodale renforce représentation spatiale
- [[concept-cognitive-mitosis-atomicity]] — Mitose cognitive : N notes indépendantes
- [[concept-collectors-fallacy-accumulation-passive]] — Collector's Fallacy : accumulation ≠ compréhension
- [[concept-context-preservation-after-mitosis]] — ## Liens annoté = mécanisme préservation post-mitose
- [[concept-physics-constraints-eliminate-nocturnal-solar-artifacts]] — Contraintes physiques éliminent artefacts solaires DL

### anti-bug (8)
- [[anti-bug-checkout-race-condition]] — setOrderPlaced avant clearCart — race condition
- [[anti-bug-claude-cli-keychain-launchd]] — Keychain inaccessible depuis launchd
- [[anti-bug-claude-jsonl-schema]] — Schéma réel JSONL conversations Claude Code
- [[anti-bug-grep-confidentiel-faux-positif]] — grep "confidentiel" = faux positif sur titre H1
- [[anti-bug-launchd-icloud-tcc]] — launchd bloqué TCC iCloud Drive
- [[anti-bug-mcp-server-scoped-vscode-only]] — MCP settings.json = scope global
- [[anti-bug-set-e-jq-missing-file]] — set -euo pipefail + jq fichier absent = exit silencieux
- [[anti-bug-zip-executable-bit-lost]] — ZIP perd bit exécutable

### decision (8)
- [[decision-architecture-hybride-second-brain]] — Architecture hybride Algo+LLM
- [[decision-bash-vs-python-boundary]] — Frontière Bash vs Python pipeline Second Brain
- [[decision-knowledge-graph-deferred]] — Knowledge Graph différé
- [[decision-mind-free-kit-first-strategy]] — Kit Gumroad first strategy
- [[decision-vault-seed-runtime-pattern]] — Pattern Vault Seed / Runtime
- [[decision-weekly-extractor-approach-c]] — Weekly extractor Approach C
- [[feature-enrichment-pipeline-approach-b]] — Approche B enrichissement vault
- [[feature-weekly-extractor-first-run]] — Weekly extractor first run validé

### discovery (8)
- [[discovery-claude-mem-architecture]] — claude-mem SQLite local offline
- [[discovery-claude-mem-privacy-risk]] — claude-mem : risque privacy observations non compartimentées
- [[discovery-facture-electronique-fr-2026]] — Facture électronique FR obligatoire sept 2026
- [[discovery-mcp-tools-print-mode]] — MCP Tools indisponibles en --print
- [[discovery-nightly-agent-architecture]] — Architecture complète nightly agent
- [[discovery-nightly-vault-api-transit]] — Vault transit API Anthropic via nightly
- [[discovery-second-brain-v4-gaps-fixes]] — 5 gaps Karpathy corrigés
- [[discovery-vault-failles-audit]] — 4 failles structurelles audit vault

### pattern (3)
- [[icloud-work-nosync-protection]] — Double protection iCloud _work.nosync/
- [[pattern-inbox-raw-layer]] — _inbox/raw/ raw input layer
- [[pattern-subagent-driven-development]] — Subagent-Driven Development multi-fichiers

### literature (5)
- [[digest-2026-W15]] — Research Digest W15
- [[digest-ai-W16]] — Digest AI W16
- [[digest-cloud-W16]] — Digest Cloud W16
- [[digest-ecommerce-W16]] — Digest ecommerce W16
- [[digest-iot-W16]] — Digest IoT W16
