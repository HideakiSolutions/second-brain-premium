#!/usr/bin/env bash
# vault-writer.sh — API normalizada de escrita no vault.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$VAULT_ROOT"
exec python3 "$SCRIPT_DIR/lib/vault_writer.py" "$@"
