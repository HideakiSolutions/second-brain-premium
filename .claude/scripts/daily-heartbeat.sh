#!/bin/bash
# Cron: daily-heartbeat
# Execução recomendada: diariamente às 07:00
# Registrado pelo install.sh:
#   0 7 * * * bash {VAULT}/_bootstrap/scripts/daily-heartbeat.sh >> {VAULT}/.logs/daily-heartbeat.log 2>&1
#
# Verifica staleness do vault e escreve _memory/heartbeat-latest.md.
# Não requer LLM — análise estrutural de arquivos.

# Auto-detectar vault: script está em _bootstrap/scripts/, vault é 2 níveis acima
VAULT="${VAULT:-$(cd "$(dirname "$0")"/../.. && pwd)}"

HEARTBEAT="$VAULT/_memory/heartbeat-latest.md"
CURRENT_STATE="$VAULT/_memory/current-state.md"
LOG="$VAULT/_memory/activity-log.md"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M')
TODAY=$(date '+%Y-%m-%d')

# Garantir que _memory/ existe
mkdir -p "$VAULT/_memory"

# Verificar staleness do current-state.md
STATE_UPDATED=$(grep "^updated:" "$CURRENT_STATE" 2>/dev/null | sed 's/updated: //' | tr -d ' ')
STATE_TS=$(date -d "${STATE_UPDATED:-2000-01-01}" +%s 2>/dev/null || echo 0)
NOW_TS=$(date +%s)
STATE_AGE=$(( (NOW_TS - STATE_TS) / 86400 ))

# Contar projetos ativos
ACTIVE_PROJECTS=0
if [ -d "$VAULT/_knowledge/projects" ]; then
  ACTIVE_PROJECTS=$(grep -rl "^status: active" "$VAULT/_knowledge/projects/" 2>/dev/null | wc -l)
fi

# Verificar flags de sessão pendente
NEEDS_END_SESSION=""
[ -f "$VAULT/_memory/.needs-end-session" ] && NEEDS_END_SESSION="true"
[ -f "$VAULT/_memory/.compacted-without-end-session" ] && NEEDS_END_SESSION="true"

# Contar fontes ingeridas (módulo opcional)
TOTAL_SOURCES=0
[ -d "$VAULT/_sources" ] && TOTAL_SOURCES=$(ls "$VAULT/_sources/"*.md 2>/dev/null | wc -l)

# Contar candidatos no backlog de promoção (módulo opcional)
BACKLOG_CANDIDATES=0
[ -f "$VAULT/_cores/promotion-backlog.md" ] && \
  BACKLOG_CANDIDATES=$(grep -c "| candidato |" "$VAULT/_cores/promotion-backlog.md" 2>/dev/null || echo 0)

# Score de saúde: começa em 10, penaliza por situações ruins
HEALTH_SCORE=10
[ "$STATE_AGE" -gt 7 ]  && HEALTH_SCORE=$((HEALTH_SCORE - 2))
[ "$STATE_AGE" -gt 14 ] && HEALTH_SCORE=$((HEALTH_SCORE - 2))
[ -n "$NEEDS_END_SESSION" ] && HEALTH_SCORE=$((HEALTH_SCORE - 1))
[ "$BACKLOG_CANDIDATES" -gt 10 ] && HEALTH_SCORE=$((HEALTH_SCORE - 1))
[ "$HEALTH_SCORE" -lt 0 ] && HEALTH_SCORE=0

# Escrever heartbeat
cat > "$HEARTBEAT" <<EOF
---
tags: [memory, heartbeat]
updated: $TODAY
---

# Vault Heartbeat — $TIMESTAMP

**Score de saúde:** $HEALTH_SCORE/10

## Estado

| Item | Valor | Status |
|------|-------|--------|
| current-state.md | atualizado há ${STATE_AGE} dias | $([ "$STATE_AGE" -le 3 ] && echo "OK" || echo "ATENCAO") |
| Projetos ativos | $ACTIVE_PROJECTS | — |
| Fontes ingeridas | $TOTAL_SOURCES | — |
| Candidatos no backlog | $BACKLOG_CANDIDATES | $([ "$BACKLOG_CANDIDATES" -le 5 ] && echo "OK" || echo "REVISAR") |
| Sessão pendente | $([ -n "$NEEDS_END_SESSION" ] && echo "sim" || echo "não") | $([ -z "$NEEDS_END_SESSION" ] && echo "OK" || echo "ATENCAO") |

## Alertas

$([ "$STATE_AGE" -gt 7 ]      && echo "- current-state.md nao atualizado ha ${STATE_AGE} dias — execute /end-session")
$([ -n "$NEEDS_END_SESSION" ]  && echo "- Sessao encerrada sem /end-session — vault pode estar desatualizado")
$([ "$BACKLOG_CANDIDATES" -gt 10 ] && echo "- ${BACKLOG_CANDIDATES} candidatos no promotion-backlog — execute /core-session para revisar")
$([ "$HEALTH_SCORE" -ge 9 ]    && echo "- Vault em boa saude, nenhuma acao necessaria")

EOF

# Activity log — sempre append (não depende de o arquivo já existir)
printf '\n## [%s] heartbeat | score %d/10 — state %d dias, %d projetos, %d fontes\n' \
  "$TIMESTAMP" "$HEALTH_SCORE" "$STATE_AGE" "$ACTIVE_PROJECTS" "$TOTAL_SOURCES" >> "$LOG"

exit 0
