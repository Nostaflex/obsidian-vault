---
type: literature
maturity: fleeting
tier: A
created: 2026-04-14
source_chain:
  - "origin: arXiv papers W16"
  - "via: paper_synthesizer.py"
papers_count: 10
domain: cloud
---

# Digest cloud W16

Tags: #cloud #digest #literature

## Tendances W16

### Décentralisation intelligente : autonomie tactique, gouvernance stratégique

La semaine révèle une architecture émergente où le contrôle se **bicéphale** : le cloud conserve la vision stratégique (placement Kubernetes via RL, orchestration globale) tandis que les agents périphériques gagnent l'autonomie tactique (perception UI continue, exécution locale). Administrative Decentralization et LogAct convergent sur ce principe : les appareils ne demandent pas permission à chaque microseconde, mais publient leurs actions dans un **log partagé** avant exécution. Cela crée une visibilité sans synchronisation bloquante—un pattern repérable dans les coflows et circuits optiques non-bloquants.

### Systèmes distribués : du quantique à l'urbain

Lamport's causality s'étend désormais aux systèmes quantiques (snapshots, global operations), tandis que la même logique relationnelle structure les graphes urbains via HyperBall. Ces deux extrêmes (microscopique quantique, macroscopique urbain) convergent sur une vérité : **estimer et compresser remplace calculer exactement**. Compteurs probabilistes pour la distance urbaine, décomposition en primitives locales pour les opérations quantiques—même économie cognitif/computationnelle.

### Fragmentation comme efficacité

LegoDiffusion éclate les pipelines monolithiques en **services autonomes découplés**, partageant composants stables (encodeurs, VAE). Cette micro-servification réduit l'empreinte mémoire et augmente le réutilisé. Parallèlement, Taming GPU Underutilization applique une logique similaire via partitionnement statique : au lieu d'un GPU partagé chaotique, des slices isolées. La révélation honteuse : les goulets cachés (alimentation, refroidissement) restent collectifs même partitionnés—isolation n'est jamais complète.

### Énergie comme métrique première

Wattlytics cristallise une tendance durable : TCO et performance ne se pensent plus séparément. GPU power varie par paliers discrets (DVFS), pas linéairement. Reduced-Mass Orbital AI fusionne panneaux solaires, radiateur et processeur dans une structure unique. L'énergie n'est plus une externalité, elle structure l'architecture matérielle elle-même.

### Signaux pour gpparts/second-brain

**1. Partitionnement statique + log partagé** : combiner l'isolation GPU déterministe avec un protocole d'intention pré-exécution crée une fiabilité agentic documentée et auditée.

**2. Causalité observationnelle** : construire des snapshots de cluster (état quorum au timestamp T) permet diagnostiquer sans rejouer l'historique entier—pertinent pour debug distribué et analyse post-mortem.

## Papers sources
- [Administrative Decentralization in Edge-Cloud Multi-Agent for Mobile Automation](http://arxiv.org/abs/2604.07767v1)
- [Asynchronous Quantum Distributed Computing: Causality, Snapshots, and Global Operations](http://arxiv.org/abs/2604.08298v1)
- [City-Scale Visibility Graph Analysis via GPU-Accelerated HyperBall](http://arxiv.org/abs/2604.08374v1)
- [LegoDiffusion: Micro-Serving Text-to-Image Diffusion Workflows](http://arxiv.org/abs/2604.08123v1)
- [LogAct: Enabling Agentic Reliability via Shared Logs](http://arxiv.org/abs/2604.07988v1)
- [NL-CPS: Reinforcement Learning-Based Kubernetes Control Plane Placement in Multi-Region Clusters](http://arxiv.org/abs/2604.08434v1)
- [Reduced-Mass Orbital AI Inference via Integrated Solar, Compute, and Radiator Panels](http://arxiv.org/abs/2604.07760v1)
- [Scheduling Coflows in Multi-Core OCS Networks with Performance Guarantee](http://arxiv.org/abs/2604.08242v1)
- [Taming GPU Underutilization via Static Partitioning and Fine-grained CPU Offloading](http://arxiv.org/abs/2604.08451v1)
- [Wattlytics: A Web Platform for Co-Optimizing Performance, Energy, and TCO in HPC Clusters](http://arxiv.org/abs/2604.08182v1)

## Liens
- [[A-2604-07760v1-1]] — concept extraction : satellite compute architecture, power-mass ratio (Reduced-Mass Orbital AI)
- [[A-2604-07767v1-1]] — concept extraction : cloud strategic control + edge tactical autonomy (Administrative Decentralization)
- [[A-2604-07767v1-2]] — concept extraction : edge UI perception for adaptive execution (Administrative Decentralization)
- [[A-2604-07988v1-1]] — concept extraction : agents publish actions in shared log before execution (LogAct)
- [[A-2604-07988v1-2]] — concept extraction : agent self-diagnosis via LLM introspection of execution log (LogAct)
- [[A-2604-08123v1-1]] — concept extraction : AI pipeline fragmentation into autonomous services (LegoDiffusion)
- [[A-2604-08123v1-2]] — concept extraction : inter-workflow model pooling reduces memory (LegoDiffusion)
- [[A-2604-08182v1-1]] — concept extraction : GPU power varies by discrete DVFS steps (Wattlytics)
- [[A-2604-08182v1-2]] — concept extraction : TCO over 5 years depends on electricity as much as hardware (Wattlytics)

<!-- generated: 2026-04-14 -->
