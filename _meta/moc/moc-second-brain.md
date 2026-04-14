---
type: moc
tag: second-brain
notes_count: 29
last_updated: 2026-04-15
scope: "auto-generated MOC for tag #second-brain"
---
# MOC — #second-brain
Generated: 2026-04-15 | 29 notes

- [[anti-bug-claude-cli-keychain-launchd]] — Les credentials Claude (OAuth via claude.ai/Max) sont dans login.keychain-db, verrouillé hors sessio
- [[anti-bug-claude-jsonl-schema]] — Les conversations Claude sont dans ~/.claude/projects/ avec répertoires path-encodés. Anti-bug criti
- [[anti-bug-grep-confidentiel-faux-positif]] — Dans integrity-check.sh, le pattern grep "confidentiel" matche le titre H1 d'une section
- [[anti-bug-launchd-icloud-tcc]] — macOS bloque l'accès de launchd à iCloud Drive via TCC. SessionCreate=true dans
- [[anti-bug-mcp-server-scoped-vscode-only]] — Les serveurs MCP configurés dans ~/.claude/settings.json sous mcpServers sont actifs uniquement dans
- [[architecture-dual-profile-vscode]] — Deux profils VSCode séparés avec LLM et accès vault distincts : Personal
- [[architecture-paper-synthesizer]] — papersynthesizer.py produit des concept extractions atomiques (Tier S/A/B), pas des digest blobs.
- [[concept-cognitive-mitosis-atomicity]] — Quand une source contient plusieurs idées distinctes, la couper en N notes
- [[concept-collectors-fallacy-accumulation-passive]] — Accumuler de l'information procure une satisfaction cognitive qui imite la compréhension sans
- [[concept-context-preservation-after-mitosis]] — Après une mitose cognitive, les notes résultantes perdent leur contexte d'origine si
- [[convention-log-anti-re-ingestion]] — meta/LOG.md est un registre append-only qui empêche la re-ingestion des fichiers déjà
- [[decision-architecture-hybride-second-brain]] — Architecture hybride Algo+LLM choisie : injection directe vault (pas de tier staging),
- [[decision-knowledge-graph-deferred]] — Ajouter un knowledge graph sur le vault a été évalué et différé
- [[decision-mind-free-kit-first-strategy]] — Le projet Guanateck (revenu annexe) vend le Second Brain Kit comme produit
- [[decision-vault-seed-runtime-pattern]] — Le repo git contient vault/ (source de vérité pour l'initialisation). Le vault
- [[decision-weekly-extractor-approach-c]] — Architecture choisie : le weekly extractor est une session Claude interactive (pas
- [[discovery-claude-mem-architecture]] — claude-mem utilise SQLite local dans ~/.claude-mem/ — offline, sans dépendance API distante.
- [[discovery-claude-mem-privacy-risk]] — Les observations claude-mem ne sont pas compartimentées par zone sensible. Une obs
- [[discovery-mcp-tools-print-mode]] — claude --print (mode non-interactif utilisé par le nightly agent) n'initialise pas le
- [[discovery-nightly-agent-architecture]] — launchd cron à 2h17 → nightly-agent.sh → claude --print .nightly-prompt.md → notes
- [[discovery-nightly-vault-api-transit]] — nightly-agent.sh concatène le contenu des fichiers vault et le transmet à claude
- [[discovery-second-brain-v4-gaps-fixes]] — Audit Karpathy de v3 a révélé 5 manques structurels → tous corrigés
- [[discovery-vault-failles-audit]] — Audit du 2026-04-10 : 4 failles structurelles identifiées dans le vault. Prochaine
- [[feature-enrichment-pipeline-approach-b]] — L'enrichissement du vault suit l'Approche B : le nightly agent consulte meta/watchlist.md
- [[feature-weekly-extractor-first-run]] — Le weekly extractor (scripts/weekly-extractor.sh + prompt Claude) a réalisé son premier run
- [[guardrail-nightly-prompt]] — Le guardrail interdisant la lecture de work.nosync/ est textuel (prompt), pas une
- [[icloud-work-nosync-protection]] — Double protection empêchant la sync iCloud des données sensibles : naming .nosync
- [[meta-purpose-lab-for-enterprise]] — Ce vault a 3 missions simultanées et explicites : 1. Lab de
- [[pattern-inbox-raw-layer]] — Le vault v4 dispose d'une zone de dépôt pour les sources externes
