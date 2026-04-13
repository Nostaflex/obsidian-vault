# Research Watchlist
<!-- Édite ce fichier dans Obsidian pour ajouter des topics de recherche -->
<!-- Le skill /notebooklm-weekly lit ce fichier automatiquement -->

## Domaines fixes (auto-managed par le skill)

| domain | arXiv categories | frequency | notebook_id |
|--------|-----------------|-----------|-------------|
| ai | cs.AI, cs.LG, cs.CL, cs.MA | weekly | <!-- auto-filled --> |
| iot | cs.NI, cs.SY, eess.SP | weekly | <!-- auto-filled --> |
| cloud | cs.DC, cs.PF | weekly | <!-- auto-filled --> |
| ecommerce | cs.IR, cs.HC | weekly | <!-- auto-filled --> |

---

## Topics custom

<!-- Format pour chaque topic :
### topic-id (kebab-case, unique)
- **Label**: Nom lisible
- **Keywords**: mot1, mot2, mot3
- **Sources**: liste de sources (arxiv:CATEGORY ou URLs)
- **Frequency**: weekly | monthly | on-demand
- **NotebookID**: <!-- auto-filled by skill -->
-->

### atomic-notes-pkm
- **Label**: Atomic Notes & Personal Knowledge Management
- **Keywords**: atomic notes, zettelkasten, personal knowledge management, PKM, evergreen notes
- **Sources**:
  - arxiv:cs.DL
  - arxiv:cs.IR
- **Frequency**: monthly
- **NotebookID**: <!-- auto-filled -->

### neural-networks-fundamentals
- **Label**: Neural Networks — Fondamentaux et Architecture
- **Keywords**: transformer architecture, attention mechanism, backpropagation, neural network theory
- **Sources**:
  - arxiv:cs.NE
  - arxiv:cs.LG
- **Frequency**: on-demand
- **NotebookID**: <!-- auto-filled -->

### gcp-event-architecture
- **Label**: GCP Event-Driven Architecture
- **Keywords**: Google Cloud Pub/Sub, Cloud Run, Eventarc, event-driven, Cloud Functions v2
- **Sources**:
  - https://cloud.google.com/pubsub/docs/overview
  - https://cloud.google.com/eventarc/docs/overview
  - https://cloud.google.com/run/docs/overview/what-is-cloud-run
- **Frequency**: on-demand
- **NotebookID**: <!-- auto-filled -->

### firebase-architecture
- **Label**: Firebase — Architecture et Patterns
- **Keywords**: Firebase Realtime Database, Firestore, Firebase Auth, offline sync, security rules
- **Sources**:
  - https://firebase.google.com/docs/database/web/structure-data
  - https://firebase.google.com/docs/firestore/data-model
  - https://firebase.google.com/docs/rules/basics
- **Frequency**: on-demand
- **NotebookID**: <!-- auto-filled -->

### event-driven-architecture
- **Label**: Event-Driven Architecture — Patterns et Implémentation
- **Keywords**: event sourcing, CQRS, message broker, Kafka, domain events, saga pattern
- **Sources**:
  - arxiv:cs.DC
  - arxiv:cs.SE
- **Frequency**: on-demand
- **NotebookID**: <!-- auto-filled -->

### nextjs-advanced-patterns
- **Label**: Next.js — Patterns avancés (Server Components, Actions)
- **Keywords**: Next.js Server Components, Server Actions, streaming, partial prerendering
- **Sources**:
  - https://nextjs.org/docs/app/building-your-application/rendering/server-components
  - https://nextjs.org/docs/app/building-your-application/data-fetching/server-actions-and-mutations
- **Frequency**: monthly
- **NotebookID**: <!-- auto-filled -->

---

## Comment ajouter un topic

1. Copier le bloc template ci-dessus
2. Changer le `topic-id` (kebab-case unique)
3. Remplir Label, Keywords, Sources, Frequency
4. Lancer `/notebooklm-weekly --topic {topic-id}` pour le traiter immédiatement
   ou attendre le run hebdomadaire si `frequency: weekly`
