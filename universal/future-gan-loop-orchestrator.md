---
type: implementation-idea
maturity: fleeting
tier: A
created: 2026-04-14
tags: [claude-code, agentic-pattern, superpowers, workflow, gan-loop]
domain: universal
source_chain:
  - "origin: discussion 2026-04-14 (session claude-code Djemil)"
  - "ref: Simon Willison — Designing agentic loops (2025-09-30)"
  - "ref: Anthropic — Harness design for long-running apps"
  - "ref: freeCodeCamp — GAN architecture for multi-agent code generation"
---

# GAN Loop orchestrator pour heavy dev — design deferred pour étude ultérieure

## Essentiel

Pattern agentique 2026 : **generator/discriminator adversarial** appliqué aux LLM agents. Orchestrateur spawne 2 sous-agents (implementer + reviewer) en boucle itérative avec état-machine explicite. Review devient **architecturalement obligatoire** — l'orchestrateur bloque tant que l'évaluateur n'a pas émis `PHASE_APPROVED`.

**Ambition visée** : formaliser ce pattern globalement (tous projets, pas juste Second Brain) en synergie avec les skills `superpowers` existantes — CLAUDE.md user-level + slash command `/gan-dev`.

**Décision 2026-04-14** : design validé, implémentation **différée**. Priorité du moment = connecter `paper_synthesizer` au nightly (TD-2026-019 γ). Revenir sur GAN Loop quand la base Second Brain est stable et qu'on a un vrai use-case heavy dev pour le tester.

## Contexte d'émergence

Découvert pendant review des angles d'optimisation du Second Brain (2026-04-13). Insight clé : les sessions Claude Code "lourdes" (multi-file, architecture, refactor) gagneraient à avoir un processus **adversarial obligatoire** plutôt que review opt-in. Les superpowers existent mais sont des briques isolées — manque l'orchestrateur qui les compose en state-machine avec enforcement.

Rechercher le terme "GAN Loop Claude Code 2026" a révélé que Simon Willison + Anthropic engineering ont déjà théorisé le pattern. Référence dominante : Willison "Designing agentic loops" (septembre 2025).

## Architecture proposée — 2 artefacts

### Artefact 1 — `~/.claude/CLAUDE.md` (user-level, doctrine globale)

S'applique à TOUS les projets Claude Code de l'utilisateur (doctrine, pas juste ce vault).

**Contenu clé** :
- Définition opérationnelle de "heavy dev" (triggers : multi-file, nouveau module, refactor > 100 LOC, architecture)
- Opt-out explicite via mots-clés ("quick fix", "just patch")
- Séquence GAN obligatoire : ideate → plan → implement (subagent) → adversarial review (subagent) → verify → finish
- Anti-patterns interdits : skip review, self-review, merge sans verify
- Signaux d'état machine : `PHASE_COMPLETE` / `CHANGES_REQUESTED {rationale}` / `PHASE_APPROVED` / `ESCALATE_USER`

### Artefact 2 — `~/.claude/commands/gan-dev.md` (slash command global)

`/gan-dev <description>` orchestre le cycle complet via subagents indépendants (contextes frais — clé de l'adversarialisme).

**Phases** :
1. Ideate (conditionnel) — superpowers:brainstorming
2. Plan (MANDATORY) — superpowers:writing-plans → `docs/plans/YYYY-MM-DD-<slug>.md`
3. Implement (subagent) — superpowers:subagent-driven-development + TDD strict
4. Adversarial Review (subagent, LOOP max 3 itérations) — superpowers:code-reviewer
   - Prompt adversarial : challenge edge cases, architecture, perf, security, test coverage
   - Sortie : `PHASE_APPROVED` ou `CHANGES_REQUESTED {liste}`
   - Si rejected → re-spawn implementer avec feedback injected
   - Après 3 iterations sans convergence → `ESCALATE_USER`
5. Verify — superpowers:verification-before-completion
6. Finish — superpowers:finishing-a-development-branch

## Synergie avec superpowers existantes

| Phase GAN | Superpower mobilisé | Rôle |
|-----------|---------------------|------|
| 1 — Ideate | brainstorming | Generator d'intent |
| 2 — Plan | writing-plans | Generator du plan |
| 3 — Implement | subagent-driven-development | Generator du code |
| 4 — Review | code-reviewer | **Discriminator** adversarial |
| 4 — Review (loop) | receiving-code-review | Implementer apprend du feedback |
| 5 — Verify | verification-before-completion | Gate evidence-based |
| 6 — Finish | finishing-a-development-branch | Exit flow (commit/push/PR) |

**Zero superpower réinventée** — tu composes l'existant dans une state-machine enforceable.

## Bénéfices

- **Uniformité** cross-project (Second Brain, GPParts, futurs repos)
- **Boot cost négligeable** (~500 tok CLAUDE.md + ~100 tok skill metadata)
- **Apprentissage itératif** : chaque run GAN alimente CLAUDE.md avec anti-patterns découverts
- **Archivage natif** : plans committés dans `docs/plans/` = traçabilité heavy dev
- **Bugs attrapés en amont** : ex. bug `custom_id 64 chars` du paper_synthesizer (2026-04-14) aurait été flaggé par un reviewer adversarial "custom_id utilisé comme str(path) sans validation de longueur — risque API limit"

## Limites / coûts

- ⚠️ **Non-enforceable hard** : CLAUDE.md est directive autorisante, pas gate bloquant. L'agent peut théoriquement skip.
- ⚠️ **Coût tokens ~3-5×** un workflow direct (impl pass + review pass + potentielles iterations). Amortissement = bugs évités + temps debug sauvé.
- ⚠️ **Max iterations arbitraire** (3) : peut frustrer si reviewer a raison mais implementer peine à fix. Besoin stratégie escalade user.
- ⚠️ **Complexity-creep risque** : ajoute infra (skill orchestrateur) au stack déjà jugé over-engineered. Aligner avec Karpathy : *"pas d'infra sans besoin empirique démontré"*.

## Critères de décision d'implémentation

**Implémenter SI** :
- Sur projet X on constate empiriquement 3+ bugs qui auraient été attrapés par review obligatoire
- Temps débogage post-commit > temps théorique review pre-commit
- Workflow manuel red-team (cf. session 2026-04-13 audit moc-index v2) ressort comme pattern récurrent

**NE PAS implémenter SI** :
- On est encore en phase "building the base" (comme actuellement sur Second Brain)
- Pas de heavy dev identifié dans les 30 prochains jours
- Coût tokens critique vs budget (GAN Loop = 3-5× un workflow simple)

## Plan de déploiement (quand décidé)

- **Étape A** (30 min) : drafter les 2 artefacts + review par user
- **Étape B** (1 semaine test) : utiliser `/gan-dev` sur UN heavy dev réel, mesurer tokens + bugs attrapés + friction
- **Étape C** (1 mois itération) : raffiner CLAUDE.md avec patterns appris, envisager promotion skill en superpower publique

## Questions ouvertes à trancher avant implémentation

1. **Versioning config globale** : committer `~/.claude/CLAUDE.md` + skill dans un repo dédié (`claude-code-doctrine`) ou dotfiles ? Cross-machine sync si multi-device ?
2. **Granularité trigger "heavy dev"** : auto-detection par compteur fichiers/LOC, ou juste mots-clés user ? Risk false positive si auto.
3. **Intégration avec outils existants** : claude-mem ? context-mode plugin ? Éviter doublons.
4. **Stratégie escalade** après 3 iterations failed : résumé auto au user ? Pause skill ? Fallback vers workflow manuel ?

## Liens

- [[pattern-subagent-driven-development]] — brique de base Phase 3
- [[architecture-token-efficient-skills]] — principes shell-first compatibles
- [[decision-bash-vs-python-boundary]] — conventions pour le skill orchestrateur (probable bash-first)
- [[A-2604-07988v1-1]] — log partagé pré-exécution, mécanisme d'auditabilité applicable au GAN loop (traçabilité generator/discriminator)
- [[A-2604-07988v1-2]] — auto-diagnostic agent via introspection du log, feedback loop comparable au discriminator adversarial

## Références externes

- Simon Willison, "Designing agentic loops", 2025-09-30 — https://simonwillison.net/2025/Sep/30/designing-agentic-loops/
- Anthropic Engineering, "Harness design for long-running application development" — https://www.anthropic.com/engineering/harness-design-long-running-apps
- freeCodeCamp, "How to Apply GAN Architecture to Multi-Agent Code Generation" — https://www.freecodecamp.org/news/how-to-apply-gan-architecture-to-multi-agent-code-generation/
- Claude Code Docs, "How the agent loop works" — https://code.claude.com/docs/en/agent-sdk/agent-loop
- MindStudio, "5 Claude Code Agentic Workflow Patterns: From Sequential to Fully Autonomous"

<!-- generated: 2026-04-14 — session Djemil + Claude, décision differer implémentation post-stabilisation Second Brain -->
