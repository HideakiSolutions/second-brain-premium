#!/usr/bin/env bash
# pattern-matrix-generator.sh — gera blocos auto delimitados em PATTERN-MATRIX e FEATURE-CATALOG.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$VAULT_ROOT"
exec python3 "$SCRIPT_DIR/lib/pattern_matrix_generator.py" "$@"
