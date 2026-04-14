---
type: concept
maturity: fleeting
tier: A
created: 2026-04-14
source_chain:
  - "origin: http://arxiv.org/abs/2604.11807v1"
  - "via: _inbox/raw/papers/ai/2026-04-13_physics_informed_state_space_models_for_reliable_solar_irrad.md"
---

# Intégrer des contraintes physiques dans un modèle deep learning élimine les prédictions solaires nocturnes impossibles

Tags: #ai #iot #solar-forecasting #physics-informed #off-grid #state-space-model

## Essentiel
Les modèles data-driven purs génèrent parfois de l'énergie solaire la nuit (artefact). Forcer la géométrie céleste comme contrainte architecturale (pas juste comme feature) supprime structurellement ces anomalies tout en améliorant la prédiction sous nuages.

## Détail
Le Thermodynamic Liquid Manifold Network projette 15 variables météo/géométriques dans une variété riemannienne linéarisée par Koopman. Un gate multiplicatif (Thermodynamic Alpha-Gate) combine l'opacité atmosphérique temps réel avec un modèle théorique ciel clair, garantissant que la sortie respecte les bornes physiques. Résultat : zéro génération fantôme nocturne et meilleure réactivité aux transitoires nuageux, crucial pour systèmes photovoltaïques off-grid autonomes.

## Liens

<!-- generated: 2026-04-14 -->
