# Convention — Prix stockés en centimes entiers

Source: GP Parts codebase (lib/utils.ts) | Vérifié: 2026-04-09 | Confiance: haute
Tags: #convention #prix #typescript #gpparts

## Essentiel

Tous les prix sont des entiers en centimes. Jamais de flottants.
Affichage via `formatPrice()` uniquement. Stockage via `parseInt()` ou valeurs littérales.

## Détail

```ts
const price = 2990; // 29,90 € — stocké en centimes
formatPrice(price); // → "29,90 €"

// ❌ INTERDIT
const price = 29.9; // erreurs d'arrondi IEEE 754 sur les calculs de TVA
```

Raison : les opérations flottantes (29.9 × 1.085) produisent des résultats comme
32.4315000000001 au lieu de 32.43. Avec des entiers en centimes (2990 × 1.085 = 3243.65
→ Math.round = 3244 centimes), le résultat est déterministe.

## Liens

- [[vat-guadeloupe-8-5]]
