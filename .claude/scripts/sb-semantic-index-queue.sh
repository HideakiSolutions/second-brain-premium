#!/usr/bin/env bash
# Enfileira arquivos alterados para reindexacao semantica incremental.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT="${VAULT:-${VAULT_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}}"
export VAULT VAULT_ROOT="${VAULT_ROOT:-$VAULT}"

if ! command -v python3 >/dev/null 2>&1; then
    exit 0
fi

exec python3 "$SCRIPT_DIR/lib/semantic_index_queue.py" queue "$@"
