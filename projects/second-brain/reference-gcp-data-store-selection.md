---
status: active
type: reference
created: 2026-04-15
tags: [reference, GCP, BigQuery, Firestore, Spanner, Cloud-SQL, data-store, architecture]
domain: second-brain
---

# Référence — GCP : Sélection data store (BigQuery / Firestore / Spanner / Cloud SQL)

## Arbre de décision

```
Workload analytique (OLAP, agrégations, requêtes ad-hoc sur gros volumes) ?
├─ Oui → BigQuery
└─ Non → Besoin de transactions globales multi-région fort consistantes ?
    ├─ Oui → Spanner
    └─ Non → App mobile/web Firebase ? Structure document flexible ?
        ├─ Oui → Firestore
        └─ Non → PostgreSQL/MySQL compatible ?
            └─ Oui → Cloud SQL
```

## Comparatif

| | BigQuery | Firestore | Spanner | Cloud SQL |
|---|---|---|---|---|
| Modèle | Colonne OLAP | Document NoSQL | Relationnel distribué | Relationnel (PG/MySQL) |
| Latence lecture | Secondes–minutes | Millisecondes | Millisecondes | Millisecondes |
| Scale | Pétaoctets | Téraoctets | Illimitée | < 100GB pratique |
| Transactions | Limitées (DML) | Optimiste multi-doc | ACID globales | ACID classiques |
| Coût | Requête ($/TB scanné) | Ops + stockage | $/node/heure | $/instance/heure |
| Index | Auto (toutes colonnes) | Explicites requis | Explicites requis | Explicites requis |

## BigQuery — points clés

- Facturation sur **données scannées** → partitionnement critique (par date ou champ)
- `PARTITION BY DATE(created_at)` + `CLUSTER BY user_id` = combo standard
- Requêtes depuis Pub/Sub, GCS, Dataflow → pipeline streaming
- `BigQuery ML` : ML sans exporter les données
- Pas adapté pour OLTP (latence trop haute, coût prohibitif à l'op unitaire)

## Firestore — points clés

- Collection → Document → Sous-collection. Pas de JOIN.
- Requêtes limitées : un seul champ de filtre inégalité par requête
- Index composites : déclarer explicitement dans `firestore.indexes.json`
- Transactions optimistes : `runTransaction()` → retry automatique sur conflit
- Règles de sécurité côté serveur : `match /users/{userId} { allow read: if request.auth.uid == userId; }`
- Offline sync native côté client (SDK JS/iOS/Android)
- **Anti-pattern** : listes longues dans un document → sous-collection obligatoire

## Spanner — points clés

- Utiliser quand : fintech, inventaire global, SLA fort de consistance
- Coût élevé (~$0.90/node/h) → pas pour petits projets
- Interleaved tables : optimisation co-localisation des données liées
- Compatible PostgreSQL (PG interface) → migration facilitée

## Cloud SQL — points clés

- Managed PostgreSQL ou MySQL — meilleure option pour apps existantes
- Max ~100 IOPS/GB → limité pour gros volumes
- High Availability : failover automatique, même région uniquement
- Préférer **Spanner** pour multi-région ou Cloud SQL + read replicas pour scale lecture

## Liens

- [[decision-gcp-compute-selection]]
- [[reference-firebase-patterns]]
