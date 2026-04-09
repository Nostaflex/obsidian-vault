# TVA Guadeloupe — Taux 8.5% (DOM-TOM)

Source: impots.gouv.fr | Vérifié: 2026-04-09 | Confiance: haute
Tags: #tva #dom-tom #guadeloupe #fiscal #gpparts

## Essentiel

TVA en Guadeloupe (code 971) : **8.5%** — différent de la France métropolitaine (20%).
Déclaré dans `lib/config.ts` : `VAT_RATE = 0.085`. Ne jamais hardcoder ailleurs.

## Détail

Les DOM utilisent un régime fiscal spécifique (octroi de mer + TVA réduite).
Le code département 971 (Guadeloupe) applique une TVA réduite sur l'ensemble des produits.

Calcul HT → TTC :

```ts
// lib/config.ts
export const VAT_RATE = 0.085;

// Usage
const priceTTC = Math.round(priceHT * (1 + VAT_RATE));
```

Toute modification du taux → uniquement dans `lib/config.ts` (source de vérité centralisée).

## Liens

- [[prix-centimes-convention]]
