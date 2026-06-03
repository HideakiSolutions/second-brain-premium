#!/usr/bin/env bash
# event-router.sh — processa fila de eventos em _memory/.events/in/.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$VAULT_ROOT"
exec python3 "$SCRIPT_DIR/lib/event_router.py" "$@"
