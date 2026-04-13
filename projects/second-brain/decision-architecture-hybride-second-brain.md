# Décision — Architecture Hybride Second Brain (Algo + LLM)

Source: _inbox/session/session-2026-04-10-weekly.md | Vérifié: 2026-04-11 | Confiance: haute
Tags: #second-brain #decision #architecture #llm #obsidian

## Essentiel
Architecture hybride Algo+LLM choisie : injection directe vault (pas de tier staging), 3 guardrails prompt-based, Obsidian comme couche de visualisation humain. Scope élargi au-delà de la stack technique (UX, design, tendances, conformité).

## Détail
- Option A (algo pur) rejetée : trop rigide pour extraction sémantique
- Option B (LLM pur) rejetée : coût trop élevé
- Tier staging (Tier 4) éliminé : injection directe avec guardrails prompt-based suffit
- Feedback Djemil validé : design approfondi avant implémentation = approche confirmée
- Watchlist étendue : UX, design, tendances en plus de la stack technique

Guardrails : 3 couches (prompt zones interdites + .nosync naming + xattr).

## Liens
- [[decision-vault-seed-runtime-pattern]]
- [[guardrail-nightly-prompt]]

<!-- generated: 2026-04-11 -->
