# Architecture — Dual Profil VSCode : Personal / Work

Source: _inbox/session/session-2026-04-10.md | Vérifié: 2026-04-11 | Confiance: haute
Tags: #second-brain #architecture #vscode #privacy #copilot #claude-code

## Essentiel
Deux profils VSCode séparés avec LLM et accès vault distincts : Personal (Claude Code + vault universel) et Work (Copilot Business Renault + _work.nosync/ isolé). Les données de travail sensibles ne transitent pas vers Anthropic.

## Détail
| Profil | LLM | Accès vault |
|---|---|---|
| Personal | Claude Code (Anthropic) | universal/, projects/, _meta/ |
| Work | GitHub Copilot Business (renault-emu) | _work.nosync/, universal/, _meta/ |

**Pourquoi Copilot Business** : garantie contractuelle de non-entraînement (Microsoft Enterprise). Opus 4.6 disponible via Copilot Chat (renault-emu a activé modèles tiers).

**Anti-bug** : Claude Code Personal ne doit JAMAIS lire le contenu de `_work.nosync/` — seulement les titres H1 dans INDEX.md.

Chaque profil a son propre `mcp.json` — configs MCP isolées.

## Liens
- [[icloud-work-nosync-protection]]
- [[guardrail-nightly-prompt]]
- [[decision-architecture-hybride-second-brain]]

<!-- generated: 2026-04-11 -->
