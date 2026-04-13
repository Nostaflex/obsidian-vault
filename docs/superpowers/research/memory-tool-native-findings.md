# Memory Tool natif — Findings

**Date**: 2026-04-13
**OQ1 du spec**: Identifier comment activer le Memory Tool natif d'Anthropic dans Claude Code CLI.
**Source**: https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool (fetched 2026-04-13)

## Verdict — NOT applicable to Claude Code CLI

Le Memory Tool natif (`memory_20250818`) est une **fonctionnalité API**, conçue pour les développeurs qui construisent leurs propres agents via le SDK Anthropic. Il **n'est pas directement utilisable depuis une session Claude Code CLI**.

## Citation officielle (verbatim)

> The memory tool operates **client-side**: you control where and how the data is stored **through your own infrastructure**.

> Since this is a **client-side tool**, Claude makes tool calls to perform memory operations, and **your application** executes those operations locally. This gives you complete control over where and how the memory is stored.

→ "Your application" = un agent custom utilisant le SDK Anthropic, pas Claude Code CLI.

## Activation dans Claude Code

**Aucun mécanisme officiel.** La doc montre uniquement l'usage via :
- `curl` direct API
- SDKs `anthropic` (Python, TS, Go, Java, C#, PHP, Ruby)
- CLI `ant messages create`

Pour utiliser le Memory Tool dans un agent, il faut implémenter les handlers (`view`, `create`, `str_replace`, `insert`, `delete`, `rename`) — soit en sous-classant `BetaAbstractMemoryTool` (Python) ou `betaMemoryTool` (TS).

Aucune mention dans la doc d'activation via `settings.json` Claude Code.

## Path de stockage

**Implementation-defined.** `/memories` est juste la racine virtuelle exposée à Claude. Le backend (filesystem, BDD, encrypted files, S3, etc.) est entièrement à la charge de l'application qui implémente les handlers.

## Compatibilité auto-memory

**Pas de couplage.** Claude Code CLI utilise déjà son propre système :
- `~/.claude/projects/<project-id>/memory/MEMORY.md` (index)
- Fichiers individuels `.md` chargés via le mécanisme `claudeMd` dans le prompt système

Les deux systèmes pourraient coexister dans une architecture custom (un agent SDK qui charge MEMORY.md de Claude Code et expose les fichiers via Memory Tool), mais c'est hors scope pour cette migration.

## Beta header

Le tool type est `memory_20250818` — pas de beta header séparé requis dans l'API standard (visible dans tous les exemples curl/SDK). Les exemples Go montrent une variante `BetaMemoryTool20250818Param` qui utilise l'endpoint `Beta.Messages.New`, suggérant qu'une version beta existe en parallèle.

## Décision pour ce projet

**→ Fallback path appliqué** (cf. plan Task 9 Step 3 et spec Section 4.3) :
- Garder l'auto-memory existant (`~/.claude/projects/-Users-djemildavid-Documents-Obsidian-KnowledgeBase/memory/`)
- Créer `user_profile.md` + `session_pointer.md` directement dans ce dossier
- Ils seront chargés via le mécanisme `claudeMd` existant
- `MEMORY.md` réduit à un pointer minimal (Phase 4 / Task 11)
- Taille cible totale ~200-300 tokens (vs 5278 tokens aujourd'hui)

## Si Memory Tool devient pertinent plus tard

Scenarios d'usage futur :
1. Migration du pipeline vers Anthropic Managed Agents (cf. memory `project_future-managed-agents.md`) → l'agent custom implémenterait le Memory Tool nativement
2. Skill avancé qui spawne des subagents via SDK pour des tâches longues → Memory Tool pour leur état persistant

Pour l'instant, **YAGNI**.
