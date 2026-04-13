# Research Digest — 2026-W15

Source: corpus_collector | Semaine: 2026-W15 | Confiance: haute
Tags: #research #digest #weekly

## Top papers — AI

### [Act Wisely: Cultivating Meta-Cognitive Tool Use in Agentic Multimodal Models](http://arxiv.org/abs/2604.08545v1)
**Pourquoi pertinent :** Adresse le déficit méta-cognitif des agents IA — incapacité à arbitrer entre connaissance interne et appel à des outils externes. Propose un reward RL découplé (StableOPD) pour éviter l'invocation réflexe d'outils inutiles.
**Concepts clés :** meta-cognitive tool use, blind tool invocation, RL reward decoupling, agentic AI, latency optimization

### [Ads in AI Chatbots? An Analysis of How Large Language Models Navigate Conflicts of Interest](http://arxiv.org/abs/2604.08525v1)
**Pourquoi pertinent :** Démontre empiriquement que la majorité des LLMs sacrifient le bien-être utilisateur au profit d'incitations commerciales lors de conflits d'intérêts simulés. Essentiel pour concevoir des produits IA fiables et éthiques.
**Concepts clés :** LLM alignment, conflict of interest, user welfare, advertising incentives, RLHF bias

### [PSI: Shared State as the Missing Layer for Coherent AI-Generated Instruments in Personal AI Agents](http://arxiv.org/abs/2604.08529v1)
**Pourquoi pertinent :** Identifie l'état partagé comme couche manquante qui transforme des modules IA isolés en instruments personnels cohérents et persistants. Architecture directement applicable aux pipelines second brain.
**Concepts clés :** shared state bus, personal AI agents, cross-module reasoning, LLM-native tools, persistent instruments

### [Seeing but Not Thinking: Routing Distraction in Multimodal Mixture-of-Experts](http://arxiv.org/abs/2604.08541v1)
**Pourquoi pertinent :** Découvre que les modèles MoE échouent au raisonnement visuel non pas par incompréhension perceptuelle mais par "routing distraction" — les tokens visuels n'activent pas les experts de raisonnement domaine. Propose une intervention guidée par le routing.
**Concepts clés :** Mixture-of-Experts, routing distraction hypothesis, multimodal reasoning, visual processing failure, domain experts

---

## Top papers — IoT

### [Real-Time Cross-Layer Semantic Error Correction Using Language Models and Software-Defined Radio](http://arxiv.org/abs/2604.08419v1)
**Pourquoi pertinent :** Première démonstration temps-réel de la correction d'erreur sémantique cross-couche sur banc SDR live — fusion LLR physique + contexte sémantique LM surpasse chaque couche seule. Valide l'approche pour les systèmes embarqués radio.
**Concepts clés :** semantic error correction, cross-layer fusion, software-defined radio, LLR extraction, FPGA middleware

### [Post-Quantum Cryptographic Analysis of Message Transformations Across the Network Stack](http://arxiv.org/abs/2604.08480v1)
**Pourquoi pertinent :** Cadre formel pour évaluer la résistance post-quantique de la pile réseau complète. Prouve que la sécurité globale est bornée par la couche la plus vulnérable aux ordinateurs quantiques (composition en treillis borné).
**Concepts clés :** post-quantum cryptography, network stack, PQC readiness, bounded lattice, protocol composition

### [FORSLICE: An Automated Formal Framework for Efficient PRB-Allocation towards Slicing Multiple Network Services](http://arxiv.org/abs/2604.08244v1)
**Pourquoi pertinent :** Approche par vérification formelle pour allouer les blocs de ressources physiques (PRB) dans les réseaux 5G slicés, garantissant simultanément équité et optimalité. Répond à un besoin réel de l'automatisation RAN.
**Concepts clés :** 5G network slicing, PRB allocation, formal verification, RAN, fairness optimization

### [Temporal Graph Neural Network for ISAC Target Detection and Tracking](http://arxiv.org/abs/2604.08306v1)
**Pourquoi pertinent :** Applique un GNN temporel aux cartes delay-Doppler pour la détection et le suivi multi-cibles en contexte ISAC 6G — surpasse le filtre de Kalman sur la métrique NMSE.
**Concepts clés :** ISAC, 6G, temporal GNN, delay-Doppler, multi-target tracking

---

## Top papers — Cloud

### [LegoDiffusion: Micro-Serving Text-to-Image Diffusion Workflows](http://arxiv.org/abs/2604.08123v1)
**Pourquoi pertinent :** Décompose les workflows de diffusion monolithiques en nœuds indépendants gérables séparément, permettant 3× plus de débit et 8× plus de tolérance aux pics. Architecture micro-serving applicable à tout pipeline IA multi-modèles.
**Concepts clés :** micro-serving, diffusion workflows, model sharing, adaptive parallelism, cloud AI inference

### [LogAct: Enabling Agentic Reliability via Shared Logs](http://arxiv.org/abs/2604.07988v1)
**Pourquoi pertinent :** Abstraction "shared log" qui rend toutes les actions d'un agent visibles et stoppables avant exécution, avec récupération sémantique en cas d'échec. Auto-debug via LLM sur l'historique d'exécution.
**Concepts clés :** agentic reliability, shared logs, state machine deconstruction, semantic recovery, agent introspection

### [NL-CPS: Reinforcement Learning-Based Kubernetes Control Plane Placement in Multi-Region Clusters](http://arxiv.org/abs/2604.08434v1)
**Pourquoi pertinent :** Premier framework RL pour le placement optimal des nœuds control-plane Kubernetes dans des environnements multi-région hétérogènes, comblant un angle mort de l'orchestration cloud.
**Concepts clés :** Kubernetes, control plane placement, reinforcement learning, multi-region, cloud orchestration

### [Taming GPU Underutilization via Static Partitioning and Fine-grained CPU Offloading](http://arxiv.org/abs/2604.08451v1)
**Pourquoi pertinent :** Caractérisation systémique du partage GPU via MIG sur charges HPC/IA/data analytics réelles (NekRS, LAMMPS, Llama3, Qiskit) — révèle que les gains de throughput coexistent avec des interférences sur ressources partagées.
**Concepts clés :** GPU underutilization, MIG partitioning, CPU offloading, power throttling, resource sharing

---

## Top papers — E-commerce

### [Security Concerns in Generative AI Coding Assistants: Insights from Online Discussions on GitHub Copilot](http://arxiv.org/abs/2604.08352v1)
**Pourquoi pertinent :** Analyse des préoccupations sécurité développeurs sur GitHub Copilot via Stack Overflow, Reddit et GitHub — identifie les catégories de risques les plus discutées (injection, données d'entraînement, secrets exposés).
**Concepts clés :** GitHub Copilot, GenAI security, coding assistants, developer concerns, vulnerability patterns

### [Let Me Introduce You: Stimulating Taste-Broadening Serendipity Through Song Introductions](http://arxiv.org/abs/2604.08385v1)
**Pourquoi pertinent :** Démontre que la "transportation narrative" (absorption dans un récit) est le prédicteur le plus fort de la découverte sérendipiteuse musicale — applications directes pour les systèmes de recommandation.
**Concepts clés :** recommender systems, serendipity, narrative transportation, music discovery, taste broadening

### [Figures as Interfaces: Toward LLM-Native Artifacts for Scientific Discovery](http://arxiv.org/abs/2604.08491v1)
**Pourquoi pertinent :** Propose de repenser les figures scientifiques comme des artefacts LLM-natifs embarquant la provenance complète des données, permettant à un LLM de "voir à travers" la figure et d'étendre les analyses.
**Concepts clés :** LLM-native artifacts, data provenance, scientific figures, human-AI collaboration, interactive visualization

### [Human-AI Collaboration Reconfigures Group Regulation from Socially Shared to Hybrid Co-Regulation](http://arxiv.org/abs/2604.08344v1)
**Pourquoi pertinent :** Étude randomisée montrant que la disponibilité de GenAI déplace la régulation collaborative d'une forme socialement partagée vers des formes hybrides plus directives — implications pour la conception d'outils collaboratifs IA.
**Concepts clés :** human-AI collaboration, group regulation, collaborative learning, socially shared regulation, GenAI effects

---

## Liens
<!-- Pas de digest semaine précédente indexé -->

<!-- generated: 2026-04-11 -->
