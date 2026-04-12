---
type: anti-bug
maturity: fleeting
tier: A
created: 2026-04-12
source_chain:
  - "origin: _inbox/session/session-2026-04-11-weekly.md"
  - "via: claude-mem obs #593 / #595"
---

# Les scripts shell perdent leur bit exécutable en ZIP si chmod +x n'est pas appliqué avant l'archivage

Tags: #anti-bug #bash #zip #packaging #chmod #shell

## Essentiel
Un fichier `.sh` extrait d'une archive ZIP n'est exécutable que si `chmod +x` a été appliqué **avant** la commande `zip`. L'archiveur ZIP préserve les permissions telles qu'elles sont au moment de l'ajout du fichier.

## Détail
Bug rencontré lors de la validation du Second Brain Kit v1.0 : `nightly-agent.sh` extrait du ZIP n'était pas exécutable. Le fichier source n'avait pas reçu `chmod +x` avant `zip -r`. Contournement dans l'installateur : `install.sh` applique `chmod +x` après extraction. Correction à la source : toujours exécuter `chmod +x *.sh` avant `zip -r archive.zip .`. Ce comportement est identique sous macOS et Linux. Différent du comportement de `tar` (qui préserve aussi les permissions, mais l'erreur est plus visible).

## Liens

<!-- generated: 2026-04-12 -->
