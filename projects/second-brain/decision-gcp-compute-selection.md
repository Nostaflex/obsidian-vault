---
status: accepted
type: architecture-decision
created: 2026-04-15
tags: [decision, GCP, cloud-run, GKE, cloud-functions, compute, architecture]
domain: second-brain
deciders: [djemild]
---

# ADR — Sélection compute GCP : Cloud Run vs GKE vs Functions

> **Contexte** : guide de décision rapide pour architecte solution — quel service compute pour quel cas.

## Arbre de décision

```
Ai-je besoin de contrôle sur l'infra (OS, GPU, réseau avancé) ?
├─ Oui → GKE (Kubernetes managé)
└─ Non → Ai-je des tâches event-driven courtes (<540s) ?
    ├─ Oui → Cloud Functions (2nd gen)
    └─ Non → Cloud Run
```

## Comparatif rapide

| Critère | Cloud Run | GKE | Cloud Functions |
|---|---|---|---|
| Unité de déploiement | Container | Pod/Deployment | Fonction source |
| Cold start | ~1-3s | Minimal (toujours up) | ~0.5-2s |
| Scale to zero | ✓ (défaut) | ✗ (min nodes) | ✓ |
| Concurrence | Par instance (1-1000) | Par pod | Par instance (1) |
| GPU | ✗ | ✓ | ✗ |
| Prix | Pay-per-request | Pay-per-node | Pay-per-invocation |
| Complexité ops | Faible | Haute | Très faible |

## Règles pour architecte

**Cloud Run** = défaut pour tout service HTTP stateless. APIs REST, microservices, workers.
- Utiliser `--min-instances 1` pour éviter cold start prod
- `--concurrency 80` est le sweet spot pour la plupart des workloads
- IAM : `roles/run.invoker` pour auth service-to-service

**GKE** = quand on a besoin de : GPU/TPU, long-running processes (>15min), stateful apps, mesh Istio, daemonsets.
- Autopilot mode : recommandé sauf besoin de node pools custom
- Workload Identity > service account key files (jamais de clés JSON en prod)

**Cloud Functions (2nd gen)** = triggers event-driven (Pub/Sub, GCS, Firestore, Eventarc).
- 2nd gen = basé sur Cloud Run → même modèle de pricing, timeout jusqu'à 60min
- 1st gen = legacy, éviter pour nouveaux projets

## IAM patterns clés

```bash
# Service account dédié par service (least privilege)
gcloud iam service-accounts create my-svc --display-name="My Service"

# Attacher rôle minimal
gcloud projects add-iam-policy-binding PROJECT \
  --member="serviceAccount:my-svc@PROJECT.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer"

# Impersonate depuis Cloud Run (Workload Identity)
# Pas de clé JSON — l'instance a son identité automatiquement
```

## Anti-patterns fréquents

- Mettre des secrets dans les env vars → utiliser Secret Manager
- Oublier `--allow-unauthenticated` en prod sans IAM → surface d'attaque
- GKE pour un simple CRUD API → over-engineering
- Functions 1st gen pour nouveaux projets → tech debt immédiat

## Liens

- [[reference-gcp-data-store-selection]]
- [[reference-firebase-patterns]]
