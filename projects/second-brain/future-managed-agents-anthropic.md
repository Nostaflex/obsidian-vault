---
status: future-implementation
priority: medium
created: 2026-04-12
tags: [future, managed-agents, anthropic, claude-code, infrastructure]
domain: second-brain
type: implementation-idea
---

# Managed Agents (Anthropic) — Future Implementation

> **Status** — 🔮 À creuser plus tard. Pas urgent, mais pertinent quand le pipeline nightly deviendra cloud-native ou qu'on voudra une UI web.

## TL;DR

**Managed Agents** est la 3ème surface de l'API Anthropic (beta, `managed-agents-2026-04-01`). Un agent **hébergé chez Anthropic** avec un **container sandbox par session** où bash/fichiers/code s'exécutent — la boucle agentique, le streaming SSE, la compaction de contexte et le caching sont gérés automatiquement.

**Flux mandatoire** : `Agent` (persisté, versionné) → `Session` (référence l'agent par ID).

---

## Architecture

```
┌─ Setup (une fois) ──┐      ┌─ Runtime (chaque run) ────┐
│ agents.create()     │ ───▶ │ sessions.create(          │
│   → store agent_id  │      │   agent=AGENT_ID,         │
│ environments.create │      │   environment_id=ENV_ID,  │
│   → store env_id    │      │   resources=[repos/files] │
└─────────────────────┘      │ )                         │
                             │ + stream events (SSE)     │
                             └───────────────────────────┘
```

### Les 4 primitives

| Primitive | Rôle | Endpoint |
|-----------|------|----------|
| **Agent** | Config persistée et versionnée : `model`, `system`, `tools`, `mcp_servers`, `skills` | `/v1/agents` |
| **Environment** | Template de container (réseau, packages) | `/v1/environments` |
| **Session** | Run actif — reference l'agent, mount des resources, stream events | `/v1/sessions` |
| **Vault** | Credentials OAuth pour MCP servers (auto-refresh par Anthropic) | `/v1/vaults` |

### Outils disponibles dans une session

- **Agent Toolset** (`agent_toolset_20260401`) : `bash`, `read`, `write`, `edit`, `glob`, `grep`, `web_fetch`, `web_search` — tous hébergés
- **MCP tools** : GitHub, Linear, Notion, NotebookLM... via vaults (credentials gérés par Anthropic)
- **Custom tools** : notre app handle l'appel via événements SSE (`agent.custom_tool_use` → `user.custom_tool_result`)

### Built-in automatiques
- Context compaction (quand on approche du max context)
- Prompt caching (historique tokens)
- Extended thinking (`agent.thinking` events)
- Session lifecycle (`running` ↔ `idle` → `terminated`)

---

## ⚠️ Claude Code ≠ Managed Agents

**Important** : Claude Code (la CLI que j'utilise actuellement) **n'est pas** un client Managed Agents. C'est un client direct de `messages.create`. Les deux surfaces **coexistent** mais ne sont pas intégrées nativement.

Claude Code utilise :
- `messages.create` + `tool_use` (boucle client-side)
- Sub-agents via le `Task` tool (in-process)
- MCP servers connectés directement au client

Managed Agents utilise :
- Boucle agentique sur l'orchestration Anthropic
- Container sandbox hébergé par Anthropic
- Event stream SSE

---

## Cas d'usage concrets pour le Second Brain

### 1. Cloud-native nightly pipeline 🌙
**Remplacer `nightly-agent.sh`** par un Managed Agent qui tourne sans que le Mac soit allumé :

```python
# scripts/managed_nightly.py
import anthropic, os
client = anthropic.Anthropic()

session = client.beta.sessions.create(
    agent=os.environ["NIGHTLY_AGENT_ID"],
    environment_id=os.environ["ENV_ID"],
    resources=[{
        "type": "github_repository",
        "url": "https://github.com/djemild/KnowledgeBase",
        "authorization_token": os.environ["GH_TOKEN"],
    }],
)
# Agent → clone repo → exécute corpus_collector + paper_synthesizer
#       → commit + push résultats → rapport via custom tool (Slack/email)
```

**Avantages** :
- Mac n'a pas besoin d'être allumé
- Sandbox isolé → pas de risque pour le vault Obsidian local
- Rollback via git facile
- Streaming events → dashboard possible

**À résoudre** :
- Remplacer les MCP locaux (NotebookLM) par une version accessible en cloud OU déplacer la partie NotebookLM côté client
- Gérer `.nightly-prompt.md` et les guards (BS-1 à BS-5) dans un agent hosted

### 2. Agent de refactor / audit one-shot 🔧
Déléguer une tâche lourde (refactor `corpus_collector`, audit sécurité, migration) à un agent qui travaille **dans un container propre** :

```python
session = client.beta.sessions.create(
    agent=REFACTOR_AGENT_ID,
    environment_id=ENV_ID,
    resources=[{"type": "github_repository", "url": "...", "authorization_token": "..."}],
)
# events.send → "Refactor paper_synthesizer pour X, commit + PR"
```

Pas de risque pour le working dir local, résultat sous forme de PR reviewable.

### 3. UI web du Second Brain 🖥️
Si un jour on veut une **interface web** pour dialoguer avec le Second Brain :
- Managed Agents stream nativement en SSE → parfait pour un dashboard React/Next.js
- Le container persiste entre messages → état maintenu côté Anthropic
- Auth Vault → OAuth pour MCP servers gérés sans stocker les tokens côté UI

### 4. Sous-agents Track B (NotebookLM) 🔄
Pour la partie grounding NotebookLM du spec hybride :
- Un agent Managed côté cloud pour la synthèse A (Claude)
- Track B NotebookLM resterait local (MCP) pour la grounding
- Orchestration via custom tool (notre client pilote les deux)

---

## Quand rester sur Claude Code (vs migrer)

### ✅ Rester Claude Code
- Développement interactif (c'est fait pour ça)
- Accès direct au vault Obsidian local
- Contrôle total sur la boucle agentique
- Déboguage pas-à-pas avec visibilité complète

### ✅ Migrer vers Managed Agents
- Pipeline headless qui tourne sans Mac allumé
- Besoin d'un sandbox filesystem isolé (pas le vault direct)
- UI custom (web dashboard)
- Config agent partageable entre machines / équipe
- Observabilité serveur (logging, tracing Anthropic-managed)

---

## Points d'attention / Pitfalls connus

1. **Agent créé une fois, pas à chaque run** — stocker `agent_id` dans config, pas dans le hot path
2. **Config sur l'agent, pas sur la session** — `model`, `system`, `tools` vont dans `agents.create()`, jamais `sessions.create()`
3. **MCP auth via vaults** — jamais dans `mcp_servers` directement (array ne prend que `type/name/url`)
4. **Stream-first ordering** — ouvrir le stream AVANT d'envoyer le message (sinon events buffered)
5. **SSE sans replay** — si la connexion drop, reconnexion + fetch history + dedupe par event ID
6. **Idle-break gate** — NE PAS break sur `session.status_idle` seul (peut être transient, ex. waiting tool_confirmation)
7. **Beta uniquement** — header `managed-agents-2026-04-01` requis (SDK auto-set)
8. **Pas disponible sur Bedrock/Vertex/Foundry** — API Anthropic directe seulement

---

## Coûts indicatifs

- Container execution : facturé à l'usage (runtime)
- Inference : tokens input/output standard (cache dispo, compaction automatique)
- Vault / Skills API : gratuit
- File storage : inclus
- Rate limits : 60 RPM create (agents/sessions/vaults), 600 RPM other — par org

---

## Prérequis avant implémentation

1. ☐ **Stabiliser Sprint 2 Track B** (NotebookLM MCP) d'abord — c'est le bloqueur actuel
2. ☐ **Décider si le vault Obsidian reste on-device ou passe partiellement cloud**
3. ☐ **Identifier quels MCP servers ont une version cloud-accessible** (NotebookLM local ≠ cloud)
4. ☐ **Designer la stratégie de secrets** (vault Anthropic OAuth vs env vars)
5. ☐ **POC minimal** : un Managed Agent qui clone le repo et lance `integrity-check.sh`

---

## Resources

- **Onboarding skill** : `claude-api managed-agents-onboard` (via Claude Code)
- **Docs officiels** : `platform.claude.com/docs/en/managed-agents/`
- **SDK Python** : `client.beta.agents` / `client.beta.sessions` / `client.beta.vaults`
- **Anthropic CLI** (`ant`) : création d'agents depuis YAML versionné

## Liens internes
- [[decision-architecture-hybride-second-brain]] — pourquoi le pipeline actuel est hybride local/cloud
- [[architecture-dual-profile-vscode]] — comment les secrets sont scopés
- [[discovery-nightly-agent-architecture]] — architecture actuelle à remplacer/complémenter
- [[decision-mind-free-kit-first-strategy]] — stratégie de priorisation (quand est-ce qu'on creuse cela)

---

**Tag** : #future-implementation #not-urgent #infrastructure-upgrade
