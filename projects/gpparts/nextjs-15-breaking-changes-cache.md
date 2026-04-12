# Next.js 15 — Breaking Changes : Cache Fetch et Async Headers

Source: https://nextjs.org/blog/next-15 | Vérifié: 2026-04-11 | Confiance: haute
Tags: #gpparts #nextjs #breaking-changes #cache #async #turbopack

## Essentiel
Next.js 15 : `fetch()` n'est plus mis en cache par défaut (opt-in requis), `next/headers` retourne une Promise. Impact gpparts : les appels API sans cache explicite peuvent dégrader les performances.

## Détail
**Breaking changes clés :**
- `fetch()` sans cache = no-store par défaut. Migration : ajouter `cache: 'force-cache'` explicitement où le cache était implicite
- `next/headers` retourne maintenant une `Promise` → requires `await`
- Composants async mieux supportés
- Turbopack recommandé pour dev (remplace webpack dev server)

**Impact gpparts :**
- Auditer tous les `fetch()` sans option `cache` explicite
- Migrer les usages de `next/headers` vers async/await
- Tester Turbopack en dev (remplacer `next dev` par `next dev --turbopack`)

## Liens
- [[discovery-nextjs-16-breaking-changes]]

<!-- generated: 2026-04-11 -->
