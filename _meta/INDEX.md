# INDEX — Knowledge Base
Updated: 2026-04-13T22:42:00+02:00 | Active: 45 notes | Ceiling: 300

## Par projet
### universal (10)
- anti-bug-set-e-jq-missing-file — set -euo pipefail + jq crashe si fichier absent
- anti-bug-zip-executable-bit-lost — chmod +x AVANT zip sinon bit exécutable perdu
- concept-cognitive-mitosis-atomicity — découper source multi-concepts en N notes atomiques
- concept-collectors-fallacy-accumulation-passive — accumulation passive imite compréhension sans produire
- concept-context-preservation-after-mitosis — annotation lien obligatoire pour contexte post-mitose
- mcp-vscode-dedicated-file — VSCode MCP config dans fichier dédié, pas settings.json
- pattern-subagent-driven-development — 1 subagent par tâche + reviewers valide qualité
- prix-centimes-convention — prix toujours en centimes entiers, formatPrice() seul
- research/digest-2026-W15 — top papers W15 2026 AI/IoT/Cloud/E-commerce curatés
- vat-guadeloupe-8-5 — TVA Guadeloupe 8.5%, distinct de métropole 20%

### projects/gpparts (4)
- anti-bug-checkout-race-condition — setOrderPlaced(true) AVANT clearCart sinon redirection
- discovery-facture-electronique-fr-2026 — réception facture électronique obligatoire France sept 2026
- discovery-nextjs-16-breaking-changes — breaking changes Next.js 16 à auditer avant migration
- nextjs-15-breaking-changes-cache — fetch no-store par défaut, next/headers retourne Promise

### projects/second-brain (31)
- anti-bug-claude-cli-keychain-launchd — login.keychain-db verrouillé hors session interactive
- anti-bug-claude-jsonl-schema — contenu dans message.content, pas d.content
- anti-bug-grep-confidentiel-faux-positif — grep matche titre H1 INDEX, pas body
- anti-bug-launchd-icloud-tcc — fix: LimitLoadToSessionType Aqua dans plist
- anti-bug-mcp-server-scoped-vscode-only — MCP servers actifs uniquement dans env qui charge config
- architecture-dual-profile-vscode — profil Personal Claude Code, profil Work Copilot Business
- architecture-paper-synthesizer — concept extractions atomiques via Gemini, anti-Collector's-Fallacy
- architecture-token-efficient-skills — ADR skills token-efficient pour Claude Code
- audit-setup-claude-code-2026-04-13 — audit complet setup Claude Code, score B+
- convention-log-anti-re-ingestion — LOG.md append-only empêche re-ingestion fichiers
- decision-architecture-hybride-second-brain — algo+LLM, injection directe vault, 3 guardrails
- decision-bash-vs-python-boundary — garder mix bash orchestration / Python traitement
- decision-knowledge-graph-deferred — différé à 100+ notes, wikilinks déjà graphe implicite
- decision-mind-free-kit-first-strategy — Guanateck vend Second Brain Kit via Gumroad
- decision-vault-seed-runtime-pattern — vault/ seed en git, runtime jamais versionné
- decision-weekly-extractor-approach-c — session interactive car --print bloque MCP tools
- discovery-claude-mem-architecture — SQLite local, ChromaDB 13Mo, daemon HTTP
- discovery-claude-mem-privacy-risk — obs non compartimentées par zone sensible
- discovery-mcp-tools-print-mode — claude --print n'initialise pas plugin system
- discovery-nightly-agent-architecture — launchd 2h17, integrity-check, output _inbox/agent/
- discovery-nightly-vault-api-transit — data flow audité, protection = guardrail prompt
- discovery-second-brain-v4-gaps-fixes — 5 gaps v3 corrigés, anti-re-ingestion validée
- discovery-vault-failles-audit — 4 failles structurelles identifiées, gaps implémentation
- feature-enrichment-pipeline-approach-b — approche B watchlist+signaux, PR#5 mergé
- feature-weekly-extractor-first-run — 350+ obs traitées, 45 concepts retenus, 14 filtrés
- future-managed-agents-anthropic — agents hébergés Anthropic avec container sandbox
- future-mcp-obsidian-server — MCP server Obsidian pour accès vault natif
- guardrail-nightly-prompt — prompt non-annulable par inbox, risque résiduel documenté
- icloud-work-nosync-protection — .nosync naming + xattr, brctl status vérification
- pattern-inbox-raw-layer — zone dépôt articles/docs/repos, ingestion auto Étape 2
- tech-debt-registry — registre dette technique pipeline second-brain

## Par type
### decisions (8)
- decision-architecture-hybride-second-brain — algo+LLM, injection directe vault
- decision-bash-vs-python-boundary — garder mix bash orchestration / Python traitement
- decision-knowledge-graph-deferred — différé à 100+ notes
- decision-mind-free-kit-first-strategy — Guanateck vend Kit via Gumroad
- decision-vault-seed-runtime-pattern — vault/ seed en git, runtime dynamique
- decision-weekly-extractor-approach-c — session interactive car --print bloque MCP
- architecture-token-efficient-skills — ADR skills token-efficient
- feature-enrichment-pipeline-approach-b — approche B watchlist+signaux

### patterns (3)
- pattern-inbox-raw-layer — zone dépôt sources externes, ingestion auto
- pattern-subagent-driven-development — 1 subagent/tâche + reviewers
- icloud-work-nosync-protection — double protection .nosync + xattr

### discoveries (10)
- discovery-claude-mem-architecture — SQLite local, ChromaDB, daemon HTTP
- discovery-claude-mem-privacy-risk — obs non compartimentées
- discovery-facture-electronique-fr-2026 — e-invoicing obligatoire sept 2026
- discovery-mcp-tools-print-mode — --print bloque plugin system
- discovery-nextjs-16-breaking-changes — breaking changes Next.js 16
- discovery-nightly-agent-architecture — launchd 2h17, workflow complet
- discovery-nightly-vault-api-transit — vault transit vers API Anthropic
- discovery-second-brain-v4-gaps-fixes — 5 gaps v3 corrigés
- discovery-vault-failles-audit — 4 failles structurelles
- feature-weekly-extractor-first-run — 350+ obs, 45 concepts retenus

### anti-bug (8)
- anti-bug-checkout-race-condition — setOrderPlaced AVANT clearCart
- anti-bug-claude-cli-keychain-launchd — keychain verrouillé hors session
- anti-bug-claude-jsonl-schema — message.content pas d.content
- anti-bug-grep-confidentiel-faux-positif — grep matche titres H1
- anti-bug-launchd-icloud-tcc — fix LimitLoadToSessionType Aqua
- anti-bug-mcp-server-scoped-vscode-only — MCP scopé à l'env actif
- anti-bug-set-e-jq-missing-file — set -e + jq fichier absent crashe
- anti-bug-zip-executable-bit-lost — chmod +x avant zip obligatoire

### concept (3)
- concept-cognitive-mitosis-atomicity — N notes indépendantes depuis 1 source
- concept-collectors-fallacy-accumulation-passive — accumulation ≠ compréhension
- concept-context-preservation-after-mitosis — annotation préserve contexte

### architecture (3)
- architecture-dual-profile-vscode — profils Personal/Work isolés
- architecture-paper-synthesizer — concept extractions atomiques Gemini
- guardrail-nightly-prompt — prompt non-annulable

### bridge (0)
_(aucune note bridge pour le moment)_

### other (10)
- audit-setup-claude-code-2026-04-13 — audit complet setup, score B+
- convention-log-anti-re-ingestion — LOG.md append-only
- future-managed-agents-anthropic — agents hébergés Anthropic
- future-mcp-obsidian-server — MCP server Obsidian natif
- mcp-vscode-dedicated-file — config MCP fichier dédié
- nextjs-15-breaking-changes-cache — fetch no-store par défaut
- prix-centimes-convention — prix centimes entiers
- research/digest-2026-W15 — top papers W15 2026
- tech-debt-registry — registre dette technique
- vat-guadeloupe-8-5 — TVA Guadeloupe 8.5%
