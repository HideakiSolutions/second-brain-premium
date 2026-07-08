#!/usr/bin/env bash
# weekly-synapse-consolidate.sh — ciclo semanal de "sono" da memoria sinaptica.
#
# Sequencia: build (grafo fresco) -> reinforce (co-ativacoes da semana) ->
# decay (enfraquece/poda aprendidas sem uso) -> consolidate (compact/expire/
# dedup/propostas/sync falkor/report).
#
# Fail-soft: qualquer fase indisponivel e pulada; o relatorio registra o que rodou.
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT_ROOT="${VAULT_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
export VAULT_ROOT VAULT="${VAULT:-$VAULT_ROOT}"
SYNAPSE="$SCRIPT_DIR/sb-synapse.sh"
LOG_PREFIX="[weekly-synapse]"

cd "$VAULT_ROOT" || exit 1

echo "$LOG_PREFIX inicio $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# valida carga da maquina antes de fase pesada (dedup embeda ~100 titulos)
LOAD="$(cut -d' ' -f1 /proc/loadavg 2>/dev/null || echo 0)"
CORES="$(nproc 2>/dev/null || echo 4)"
HEAVY_OK=1
if command -v python3 >/dev/null 2>&1; then
  HEAVY_OK="$(python3 -c "print(1 if float('$LOAD') < int('$CORES') else 0)" 2>/dev/null || echo 1)"
fi

bash "$SYNAPSE" build || echo "$LOG_PREFIX build falhou (segue)"
bash "$SYNAPSE" reinforce --window 10080 || echo "$LOG_PREFIX reinforce falhou (segue)"
bash "$SYNAPSE" decay || echo "$LOG_PREFIX decay falhou (segue)"

if [ "$HEAVY_OK" = "1" ]; then
  bash "$SYNAPSE" consolidate || echo "$LOG_PREFIX consolidate falhou"
else
  echo "$LOG_PREFIX load alto ($LOAD/$CORES cores) — consolidate sem dedup"
  bash "$SYNAPSE" consolidate --no-dedup || echo "$LOG_PREFIX consolidate falhou"
fi

# rastro no activity log (append-only)
TS="$(date '+%Y-%m-%d %H:%M')"
echo "" >> _memory/activity-log.md
echo "## [$TS] heartbeat | synapse-consolidate semanal (relatorio: _memory/synapse-report.md)" >> _memory/activity-log.md

echo "$LOG_PREFIX fim $(date -u +%Y-%m-%dT%H:%M:%SZ)"
