# Pattern — _inbox/raw/ Input Layer (Karpathy Raw Input Zone)

Source: _inbox/session/session-2026-04-11.md | Vérifié: 2026-04-12 | Confiance: haute
Tags: #second-brain #pattern #inbox #raw #architecture #karpathy

## Essentiel
Le vault v4 dispose d'une zone de dépôt pour les sources externes (articles, docs, repos).
L'agent nocturne les ingère automatiquement en notes atomiques lors de l'Étape 2.

## Détail

Structure créée en v4 :
```
_inbox/raw/
  articles/   ← articles web, blog posts
  docs/        ← documentation officielle
  repos/       ← README, extraits de code
  _processed/  ← destination après ingestion
```

**Convention source-url** : si la première ligne du fichier contient `<!-- source-url: URL -->`, l'agent utilise cette URL comme champ `Source:` de la note atomique générée.

**Workflow** :
1. Déposer un fichier `.md` dans le sous-dossier approprié
2. Optionnel : ajouter `<!-- source-url: URL -->` en première ligne
3. L'agent nocturne traite à l'Étape 2 et déplace vers `_processed/YYYY-MM-DD-nomfichier.md`

Ce pattern répond au Gap 1 de l'audit Karpathy : séparation raw input / wiki compilé / schéma structuré.

## Liens
- [[discovery-second-brain-v4-gaps-fixes]] — gap Karpathy #1 que ce pattern corrige
- [[discovery-nightly-agent-architecture]] — agent qui traite cette couche à l'Étape 2
- [[concept-collectors-fallacy-accumulation-passive]] — ce pattern est la réponse architecturale au piège d'accumulation passive

<!-- generated: 2026-04-12 -->
