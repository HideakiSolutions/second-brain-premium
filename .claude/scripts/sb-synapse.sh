#!/usr/bin/env bash
# sb-synapse.sh — CLI da camada sinaptica (build/recall/explain/reinforce/decay/consolidate).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SYNAPSE="$VAULT_ROOT/_bootstrap/agentic/synapse/main.py"
cd "$VAULT_ROOT"
export VAULT_ROOT
export PYTHONUTF8=1

if command -v py >/dev/null 2>&1; then
    PYTHON="py -3"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
else
    PYTHON="python"
fi

exec $PYTHON "$SYNAPSE" "$@"
