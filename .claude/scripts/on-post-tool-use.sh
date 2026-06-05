#!/usr/bin/env bash
# on-post-tool-use.sh — Hook PostToolUse do Claude Code.
#
# Lê JSON do stdin, bloqueia secrets em alvos sensiveis e valida o arquivo
# editado se ele estiver no vault.
# Modo bloqueante controlado por LINT_STRICT (default 0 = warning-only).
#
# Não falhar nunca — política de "warning-first" para os 7 primeiros dias.
set -eu

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT_ROOT="${VAULT_ROOT:-${VAULT:-$(cd "$SCRIPT_DIR/../.." && pwd)}}"
export VAULT_ROOT VAULT="${VAULT:-$VAULT_ROOT}"
VALIDATOR="$SCRIPT_DIR/lib/post_tool_use_validator.py"
INPUT=$(cat)

if ! command -v python3 >/dev/null 2>&1; then
    exit 0
fi

cd "$VAULT_ROOT"

printf '%s' "$INPUT" | bash "$SCRIPT_DIR/secret-leak-guard.sh" tool || rc=$?
rc="${rc:-0}"
if [ "$rc" -eq 2 ]; then
    exit 2
fi

printf '%s' "$INPUT" | python3 "$VALIDATOR" || rc=$?
rc="${rc:-0}"
if [ "${LINT_STRICT:-0}" = "1" ] && [ "$rc" -eq 2 ]; then
    exit 2
fi

printf '%s' "$INPUT" | bash "$SCRIPT_DIR/sb-semantic-index-queue.sh" >/dev/null 2>&1 || true
exit 0
