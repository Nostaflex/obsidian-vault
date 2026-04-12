# Découverte — Nightly Agent : Contenu Vault Transit vers API Anthropic

Source: _inbox/session/session-2026-04-10-weekly.md | Vérifié: 2026-04-11 | Confiance: haute
Tags: #second-brain #discovery #nightly-agent #privacy #anthropic #api #security

## Essentiel
`nightly-agent.sh` concatène le contenu des fichiers vault et le transmet à `claude CLI` → API Claude (Anthropic). Tout fichier non exclu par le guardrail prompt transite par l'API. La protection repose sur le prompt "Zones interdites", **pas sur un sandbox filesystem**.

## Détail
**Data flow audité** :
```
vault content → nightly-agent.sh → claude --print → Anthropic API
```

**Trois couches de protection** pour les zones sensibles :
1. Naming `.nosync` → exclusion iCloud
2. `xattr` com.apple.fileprovider.ignore#P → exclusion iCloud (double)
3. Guardrail prompt dans `.nightly-prompt.md` → exclusion logique dans le run

**Risque résiduel** : couche 3 = prompt engineering. Si le guardrail est contourné, le contenu transite vers Anthropic.

## Liens
- [[guardrail-nightly-prompt]]
- [[icloud-work-nosync-protection]]

<!-- generated: 2026-04-11 -->
