#!/usr/bin/env bash
# curator.sh — wrapper para o self-curation agent
# Uso: bash .claude/scripts/curator.sh [scan|report|clear]
set -euo pipefail

VAULT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CURATOR_DIR="$VAULT_ROOT/_bootstrap/agentic/curator"

CMD="${1:-scan}"

if [[ "$CMD" != "scan" && "$CMD" != "report" && "$CMD" != "clear" ]]; then
    echo "Uso: curator.sh [scan|report|clear]" >&2
    exit 1
fi

# Executar com Python do curator dir no PYTHONPATH para imports relativos
cd "$CURATOR_DIR"
exec python3 main.py "$CMD"
