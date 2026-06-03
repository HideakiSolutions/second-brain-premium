#!/usr/bin/env bash
# concept-extractor.sh — gera _index/CONCEPT-INDEX.md a partir de _decisions/ e _learnings/.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$VAULT_ROOT"
exec python3 "$SCRIPT_DIR/lib/concept_extractor.py" "$@"
