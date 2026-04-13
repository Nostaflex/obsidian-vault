---
type: architecture
tier: A
created: 2026-04-13
tags: [second-brain, paper-synthesizer, anthropic-batch, pipeline]
domain: second-brain
---

# Paper Synthesizer — Architecture

## Essentiel
`paper_synthesizer.py` produit des **concept extractions atomiques** (Tier S/A/B), pas des digest blobs. C'est une doctrine anti-Collector's-Fallacy : chaque concept extrait est une unité indépendante testable.

## Stack
- **Model**: Claude Haiku via Anthropic Batch API (migré depuis Gemini EU-bloqué, F22)
- **Cache**: `cache_control: ephemeral` pour shared context entre batch items
- **Poll interval**: 60 secondes sur batch status
- **Output**: `_inbox/raw/concepts/{tier}-*.md` pour Tier S/A; digest 1-ligne pour Tier B

## Tier filter
- **Tier S**: concept central du Mind Map + ≥ 2 sous-questions non-triviales → pre-note atomique
- **Tier A**: concept Study Guide avec ≥ 1 sous-question → pre-note atomique
- **Tier B**: mentionné en 1 phrase sans sous-question → 1-liner dans digest

## Liens
- [[decision-weekly-extractor-approach-c]] — approche C validée
- [[feature-weekly-extractor-first-run]] — premier run 45 concepts
- [[decision-architecture-hybride-second-brain]] — architecture globale

<!-- Migré depuis memory/project_paper-synthesizer-pipeline.md (2026-04-13) -->
