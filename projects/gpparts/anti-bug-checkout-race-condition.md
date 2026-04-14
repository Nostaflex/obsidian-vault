# Anti-bug — Race condition checkout GP Parts

Source: GP Parts CLAUDE.md (Bug #3) | Vérifié: 2026-04-09 | Confiance: haute
Tags: #gpparts #bug #checkout #race-condition #react

## Essentiel

`setOrderPlaced(true)` AVANT `clearCart()`. Jamais l'inverse.
Inverser cet ordre redirige vers /panier au lieu de /commande/confirmation.

## Détail

```tsx
// ✅ CORRECT — flag avant action
setOrderPlaced(true);
clearCart();
router.push("/commande/confirmation");

// ❌ INTERDIT — clearCart() avant le flag
// clearCart() déclenche une écoute du panier vide → redirection /panier
// router.push('/commande/confirmation') n'est jamais atteint
clearCart();
router.push("/commande/confirmation");
```

Ce bug est silencieux : pas d'erreur console, juste une mauvaise redirection.
Le flag `orderPlaced` doit être vrai AVANT toute mutation d'état global.

## Liens

_(voir aussi : anti-bug-nesting-a-button — note à créer)_
- [[discovery-facture-electronique-fr-2026]]
- [[nextjs-15-breaking-changes-cache]]
- [[A-2604-07767v1-1]] — architecture cloud stratégique + edge tactique autonome, pertinent pour la séparation des responsabilités côté gpparts
- [[A-2604-07767v1-2]] — perception UI edge pour exécution adaptative, lié aux problèmes d'état UI comme cette race condition
