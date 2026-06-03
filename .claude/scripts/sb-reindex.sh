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

if [ "${1:-}" = "status" ]; then
    exec python3 "$INDEXER" status
fi

if [ "${1:-}" = "--paths" ]; then
    shift
    exec python3 "$INDEXER" reindex --replace --paths "$@"
fi

exec python3 "$INDEXER" reindex --replace "$@"
