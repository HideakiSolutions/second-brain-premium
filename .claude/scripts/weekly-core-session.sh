#!/bin/bash
# Cron: weekly-core-session
# Execução recomendada: toda segunda-feira às 09:30
# Registrado pelo install.sh:
#   30 9 * * 1 bash {VAULT}/_bootstrap/scripts/weekly-core-session.sh >> {VAULT}/.logs/weekly-core-session.log 2>&1
#
# Módulo opcional: só executa se _cores/ existir no vault.
# Analisa o promotion-backlog e gera relatório de drift semanal.
# Não requer LLM — análise estrutural de arquivos.

# Auto-detectar vault: script está em _bootstrap/scripts/, vault é 2 níveis acima
VAULT="${VAULT:-$(cd "$(dirname "$0")"/../.. && pwd)}"

# Módulo opcional: sair silenciosamente se _cores/ não existe
[ -d "$VAULT/_cores" ] || exit 0

BACKLOG="$VAULT/_cores/promotion-backlog.md"
REPORT="$VAULT/_cores/weekly-report-latest.md"
HEARTBEAT="$VAULT/_memory/heartbeat-latest.md"
LOG="$VAULT/_memory/activity-log.md"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M')
TODAY=$(date '+%Y-%m-%d')

# Garantir que _memory/ existe
mkdir -p "$VAULT/_memory"

# Contar candidatos no backlog por status
TOTAL_CANDIDATES=0
IN_ANALYSIS=0
PROMOTED=0
if [ -f "$BACKLOG" ]; then
  TOTAL_CANDIDATES=$(grep -c "| candidato |" "$BACKLOG" 2>/dev/null); TOTAL_CANDIDATES=$(( ${TOTAL_CANDIDATES:-0} + 0 ))
  IN_ANALYSIS=$(grep -c "| em análise |" "$BACKLOG" 2>/dev/null); IN_ANALYSIS=$(( ${IN_ANALYSIS:-0} + 0 ))
  PROMOTED=$(grep -c "| promovido |" "$BACKLOG" 2>/dev/null); PROMOTED=$(( ${PROMOTED:-0} + 0 ))
fi

# Verificar idade da última revisão do backlog
LAST_REVIEW=$(grep "^> Última varredura" "$BACKLOG" 2>/dev/null | tail -1 | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}')
LAST_TS=$(date -d "${LAST_REVIEW:-2000-01-01}" +%s 2>/dev/null || date -j -f "%Y-%m-%d" "${LAST_REVIEW:-2000-01-01}" +%s 2>/dev/null || echo 0)
LAST_TS=$(( ${LAST_TS:-0} + 0 ))
NOW_TS=$(date +%s)
BACKLOG_AGE=$(( (NOW_TS - LAST_TS) / 86400 ))

# Escrever relatório semanal
cat > "$REPORT" <<EOF
---
tags: [core, registry, weekly-report]
updated: $TODAY
---

# Core Session — Weekly Report

**Gerado em:** $TIMESTAMP

## Backlog de Promoção

| Status | Count |
|--------|-------|
| candidatos | $TOTAL_CANDIDATES |
| em análise | $IN_ANALYSIS |
| promovidos | $PROMOTED |

**Última revisão humana:** ${LAST_REVIEW:-desconhecida} (${BACKLOG_AGE} dias atrás)

$([ "$BACKLOG_AGE" -gt 14 ] && echo "- ALERTA: backlog sem revisão há ${BACKLOG_AGE} dias. Execute /core-session para analisar.")
$([ "$TOTAL_CANDIDATES" -gt 5 ] && echo "- ALERTA: ${TOTAL_CANDIDATES} candidatos acumulados. Considere sprint de promoção ao core.")

## Ação Recomendada

$([ "$TOTAL_CANDIDATES" -gt 0 ] && echo "- Execute \`/core-session\` para revisar candidatos e identificar novos gaps")
$([ "$BACKLOG_AGE" -gt 7 ] && echo "- Revisar e mover candidatos para 'em análise' ou 'rejeitado'")
$([ "$PROMOTED" -gt 0 ] && echo "- ${PROMOTED} feature(s) promovida(s) — verificar se FEATURE-CATALOG foi atualizado")
$([ "$TOTAL_CANDIDATES" -eq 0 ] && [ "$BACKLOG_AGE" -le 7 ] && echo "- Backlog em dia, nenhuma ação necessaria.")

EOF

# Alerta crítico no heartbeat se backlog muito antigo
if [ "$BACKLOG_AGE" -gt 14 ] && [ -f "$HEARTBEAT" ]; then
  printf '\n## Core Drift Alert (%s)\n%d candidatos sem revisão há %d dias. Execute /core-session.\n' \
    "$TODAY" "$TOTAL_CANDIDATES" "$BACKLOG_AGE" >> "$HEARTBEAT"
fi

# Atualizar timestamp de varredura no backlog
if [ -f "$BACKLOG" ]; then
  sed -i "s|^> Última varredura automática:.*|> Última varredura automática: $TODAY (cron weekly-core-session)|" "$BACKLOG"
fi

# Activity log — sempre append
printf '\n## [%s] heartbeat | core-session semanal: %d candidatos, %d em análise, %d promovidos\n' \
  "$TIMESTAMP" "$TOTAL_CANDIDATES" "$IN_ANALYSIS" "$PROMOTED" >> "$LOG"

exit 0
