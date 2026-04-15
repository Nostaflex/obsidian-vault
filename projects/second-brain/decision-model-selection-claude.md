---
status: accepted
type: architecture-decision
created: 2026-04-15
tags: [decision, claude, LLM, model-selection, opus, sonnet, haiku, API]
domain: second-brain
deciders: [djemild]
---

# ADR — Sélection de Modèle Claude (Opus / Sonnet / Haiku)

> **Décision** : choisir le modèle selon la tâche, pas par défaut ou confort.
> **Date** : 2026-04-15
> **Statut** : Accepted
> **Source** : S177 — session analyse architecture second brain

## Règle de sélection

| Cas | Modèle | Pourquoi |
|---|---|---|
| Analyse multi-expert, design critique, ADR complexe | **Opus 4.6** | Raisonnement profond, multi-turn complexe |
| Implémentation standard, code, debug, pipeline | **Sonnet 4.6** | Meilleur ratio perf/coût, vitesse acceptable |
| Triage, classification, extraction structurée, batch | **Haiku 4.5** | Ultra-rapide, coût minimal, tâches répétitives |

## Model IDs (API)

```python
OPUS    = "claude-opus-4-6"
SONNET  = "claude-sonnet-4-6"   # défaut pour la plupart des agents
HAIKU   = "claude-haiku-4-5-20251001"
```

## Heuristiques pratiques

- **Opus** : session interactive où le raisonnement est le produit (brainstorming, ADR, red-team). PAS pour du code boilerplate.
- **Sonnet** : subagents d'implémentation, review code, génération de plans. 90% des cas.
- **Haiku** : preprocessing, scoring, classification, tâches headless sans contexte riche.

## Coût relatif approximatif

Opus ≈ 15× Haiku côté input, Sonnet ≈ 3× Haiku. Batch API = -50% sur input.

## Anti-patterns

- Utiliser Opus pour tout "par sécurité" → budget brûlé sans gain
- Utiliser Haiku pour du raisonnement multi-step → erreurs silencieuses
- Ne pas pinner le model ID en prod → comportement change à chaque release

## Liens

- [[reference-claude-api-key-features]]
- Spec CLaRa ADR : `docs/superpowers/specs/2026-04-15-clara-inspired-rag-adr.md`
