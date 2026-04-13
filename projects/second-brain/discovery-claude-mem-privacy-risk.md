# Découverte — claude-mem : Risque Privacy (observations non compartimentées)

Source: _inbox/session/session-2026-04-10-weekly.md | Vérifié: 2026-04-11 | Confiance: haute
Tags: #second-brain #discovery #claude-mem #privacy #security #risk

## Essentiel
Les observations claude-mem ne sont pas compartimentées par zone sensible. Une obs créée lors d'une session incluant des données sensibles peut contenir ces données dans son contenu, même si le titre paraît neutre.

## Détail
**Risque identifié** : le weekly extractor filtre sur titre + fichier associé, mais pas sur le contenu complet des obs (coût token trop élevé pour filtrage exhaustif).

**Mitigation actuelle** : filtre sur mots-clés dans le titre uniquement.

**Mitigation complémentaire recommandée** : convention de nommage pour les obs sensibles (préfixe `WORK:` ou similaire) pour faciliter le filtrage titre.

Impact : toute observation créée en session Work (données Renault, architecture interne) peut théoriquement se retrouver dans le weekly extractor si le titre est neutre.

## Liens
- [[discovery-claude-mem-architecture]]
- [[decision-weekly-extractor-approach-c]]
- [[architecture-dual-profile-vscode]]

<!-- generated: 2026-04-11 -->
