#!/usr/bin/env bash
# auto-linker.sh — wrapper bash do auto_linker.py
#
# Uso:
#   .claude/scripts/auto-linker.sh                   # dry-run vault inteiro
#   .claude/scripts/auto-linker.sh --apply           # grava mudanças
#   .claude/scripts/auto-linker.sh --scope _knowledge/projects/meu-projeto
#   .claude/scripts/auto-linker.sh --apply --scope _knowledge/projects/meu-projeto

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PY="$SCRIPT_DIR/lib/auto_linker.py"

if ! command -v python3 >/dev/null 2>&1; then
    echo "[auto-linker] python3 não encontrado" >&2
    exit 1
fi

cd "$VAULT_ROOT"
exec python3 "$PY" "$@"
