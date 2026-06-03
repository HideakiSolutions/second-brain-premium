#!/usr/bin/env bash
# style-validator.sh — valida rascunho contra fingerprint.
#
# Uso:
#   echo "rascunho" | bash .claude/scripts/style-validator.sh
#   bash .claude/scripts/style-validator.sh --file rascunho.md --format md
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/lib/style_validator.py" "$@"
