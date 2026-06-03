#!/usr/bin/env bash
# predict.sh - wrapper bash para o predictor de proximas tarefas.
#
# Uso:
#   bash .claude/scripts/predict.sh --project <slug> [--k 5]
#   bash .claude/scripts/predict.sh types-distribution --project <slug>
#
# Variaveis de ambiente respeitadas:
#   SB_VAULT_ROOT   - raiz do vault (padrao: $VAULT)
#   ANTHROPIC_API_KEY - se definida, usa LLM; caso contrario, fallback deterministico

set -euo pipefail

VAULT_ROOT="${SB_VAULT_ROOT:-$VAULT}"
PREDICTOR_DIR="${VAULT_ROOT}/_bootstrap/agentic/predictor"
PYTHON="${PYTHON:-python3}"

# Detecta se o primeiro argumento e um subcomando conhecido
SUBCMD="predict"
if [[ "${1:-}" == "types-distribution" ]]; then
    SUBCMD="types-distribution"
    shift
fi

exec "$PYTHON" "${PREDICTOR_DIR}/main.py"     --vault "${VAULT_ROOT}"     "${SUBCMD}"     "$@"
