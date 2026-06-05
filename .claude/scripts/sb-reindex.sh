#!/usr/bin/env bash
# sb-reindex.sh — re-indexa o vault no Qdrant.
#
# Uso:
#   sb-reindex.sh                                    # vault inteiro, --replace
#   sb-reindex.sh --paths file1.md file2.md          # paths específicos
#   sb-reindex.sh status                             # status da infra
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
INDEXER="$VAULT_ROOT/_bootstrap/agentic/indexer/main.py"
cd "$VAULT_ROOT"
export VAULT_ROOT
# Console Windows usa cp1252 por padrão; força UTF-8 no Python (no-op em Linux/macOS).
export PYTHONUTF8=1

# Resolve interpretador Python: 'py' (launcher Windows) tem prioridade porque
# 'python3' no Windows pode ser o stub da Microsoft Store, que falha em runtime.
if command -v py >/dev/null 2>&1; then
    PYTHON="py -3"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
else
    PYTHON="python"
fi

if [ "${1:-}" = "status" ]; then
    exec $PYTHON "$INDEXER" status
fi

if [ "${1:-}" = "--paths" ]; then
    shift
    exec $PYTHON "$INDEXER" reindex --replace --paths "$@"
fi

exec $PYTHON "$INDEXER" reindex --replace "$@"
