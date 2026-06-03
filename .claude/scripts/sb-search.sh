#!/usr/bin/env bash
# sb-search.sh — busca semântica no vault via Qdrant + Ollama bge-m3.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
INDEXER="$VAULT_ROOT/_bootstrap/agentic/indexer/main.py"
cd "$VAULT_ROOT"
exec python3 "$INDEXER" search "$@"
