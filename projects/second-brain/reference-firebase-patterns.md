---
status: active
type: reference
created: 2026-04-15
tags: [reference, Firebase, Firestore, security-rules, App-Check, Cloud-Functions, Emulator, architecture]
domain: second-brain
---

# Référence — Firebase : Patterns architecte solution

## 1. Security Rules — patterns essentiels

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    // Auth requis pour tout
    match /{document=**} {
      allow read, write: if false; // deny by default
    }

    // User peut lire/écrire ses propres données uniquement
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }

    // Lecture publique, écriture owner uniquement
    match /posts/{postId} {
      allow read: if true;
      allow write: if request.auth != null
                   && request.auth.uid == resource.data.authorId;
    }

    // Validation de données (schema enforcement)
    match /orders/{orderId} {
      allow create: if request.auth != null
                    && request.resource.data.amount is number
                    && request.resource.data.amount > 0
                    && request.resource.data.userId == request.auth.uid;
    }
  }
}
```

**Règles de sécurité** :
- `request.resource` = données en cours d'écriture
- `resource` = données existantes en base
- Ne jamais `allow read, write: if true` en prod
- Tester avec Firebase Emulator avant deploy

## 2. Firestore Data Modeling

### Fan-out vs sub-collections

```
// ✗ Anti-pattern : liste dans document
/users/{uid} → { friends: ["uid1", "uid2", ...] }  // limité à ~1MB doc

// ✓ Sous-collection
/users/{uid}/friends/{friendId} → { addedAt: timestamp }
```

### Dénormalisation pour performance

```
// Dupliquer les champs souvent lus — cohérence maintenue via Cloud Functions
/posts/{postId} → {
  authorId: uid,
  authorName: "Alice",   // dupliqué depuis /users/{uid}
  authorAvatar: url      // évite un JOIN côté client
}
```

### Pagination curseur (pas offset)

```javascript
// ✓ Curseur — scalable
const next = query(collection, orderBy("createdAt"), startAfter(lastDoc), limit(20));

// ✗ Offset — scanne toujours depuis le début
```

## 3. App Check

Protège les backends Firebase contre les clients non autorisés (apps non officielles, scripts).

```javascript
// Init App Check (web) avec reCAPTCHA v3
initializeAppCheck(app, {
  provider: new ReCaptchaV3Provider(SITE_KEY),
  isTokenAutoRefreshEnabled: true
});
```

- Providers : reCAPTCHA Enterprise (web), App Attest (iOS), Play Integrity (Android), DeviceCheck
- En mode **enforcement** : requêtes sans token valide → rejetées par Firestore/Functions/Storage
- **Debug token** pour environnement de dev (jamais en prod)
- Activer en "monitoring" d'abord → analyser le trafic → enforcer

## 4. Cloud Functions vs Extensions

| | Cloud Functions | Firebase Extensions |
|---|---|---|
| Flexibilité | Totale | Limitée au template |
| Maintenance | À ta charge | Communauté / Firebase |
| Config | Code | Variables d'env UI |
| Coût | Identique (même runtime) | Identique |
| Use case | Logique métier custom | Cas standard (resizing, stripe, algolia) |

**Règle** : Extensions pour les cas couverts (image resize, Stripe payments, Algolia sync). Functions pour tout le reste.

```javascript
// Function typique — trigger Firestore
exports.onUserCreate = onDocumentCreated("/users/{uid}", async (event) => {
  const data = event.data?.data();
  await sendWelcomeEmail(data.email);
});

// HTTP callable (auth incluse automatiquement)
exports.createOrder = onCall({ region: "europe-west1" }, async (request) => {
  if (!request.auth) throw new HttpsError("unauthenticated", "Login required");
  // ...
});
```

## 5. Firebase Emulator Suite

Environnement local complet — Firestore, Auth, Functions, Storage, Pub/Sub.

```bash
firebase emulators:start
# UI : http://localhost:4000
```

```javascript
// Connecter l'app aux émulateurs en dev
if (process.env.NODE_ENV === 'development') {
  connectFirestoreEmulator(db, 'localhost', 8080);
  connectAuthEmulator(auth, 'http://localhost:9099');
  connectFunctionsEmulator(functions, 'localhost', 5001);
}
```

- **Tester les security rules** : `firebase emulators:exec --only firestore "npm test"`
- Export/Import data : `--export-on-exit ./emulator-data` + `--import ./emulator-data`
- Indispensable avant tout deploy — jamais tester les rules directement en prod

## Liens

- [[decision-gcp-compute-selection]]
- [[reference-gcp-data-store-selection]]
