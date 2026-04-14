#!/bin/bash
# paper-synthesizer.sh — Wrapper qui charge ANTHROPIC_API_KEY depuis macOS Keychain
# et invoque paper_synthesizer.py.
#
# Résout TD-2026-019 (paper_synthesizer orphan — jamais branché en prod faute de
# plomberie pour la clé API). Pattern identique au bootstrap `github-pat` (cf.
# [[decision-security-secrets-in-keychain]] — TD-2026-001).
#
# Pré-requis :
#   security add-generic-password -U -a $USER -s anthropic-api-key -w "sk-ant-..."
#
# Usage :
#   ./paper-synthesizer.sh [--domain ai|iot|cloud|ecommerce] [--dry-run] [--week N] [--min-tier S|A|B]
#
# Pour lancer depuis launchd ou nightly-agent.sh : invoquer ce wrapper, pas le .py directement.

set -euo pipefail

VAULT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load API key from Keychain (fail fast if absent — évite le fallback silencieux)
if ! KEY=$(security find-generic-password -a "$USER" -s anthropic-api-key -w 2>/dev/null); then
  echo "❌ ANTHROPIC_API_KEY introuvable dans Keychain (service 'anthropic-api-key', account '$USER')." >&2
  echo "   Pour la stocker :" >&2
  echo "     security add-generic-password -U -a \$USER -s anthropic-api-key -w 'sk-ant-...'" >&2
  exit 1
fi

# Sanity check : clé non-vide et format plausible (sk-ant-...)
if [ -z "$KEY" ] || [[ "$KEY" != sk-ant-* ]]; then
  echo "❌ Clé récupérée du Keychain ne ressemble pas à une clé Anthropic (attendu: sk-ant-...)." >&2
  exit 1
fi

export ANTHROPIC_API_KEY="$KEY"

# Invoque le module Python avec tous les args passés
exec python3 "$VAULT/paper_synthesizer.py" "$@"
