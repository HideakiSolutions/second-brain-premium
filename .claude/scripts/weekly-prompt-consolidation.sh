#!/bin/bash
# Cron: weekly-prompt-consolidation
# Execução recomendada: todo domingo às 23:00
# Registrado pelo install.sh:
#   0 23 * * 0 bash {VAULT}/_bootstrap/scripts/weekly-prompt-consolidation.sh >> {VAULT}/.logs/weekly-prompt-consolidation.log 2>&1
#
# Verifica se há prompts acumulados suficientes para análise.
# Se sim, cria flag .consolidation-ready — o hook exibe o aviso no próximo prompt.
# A análise real (com LLM) acontece quando o usuário roda /consolidate-prompts.

# Auto-detectar vault: script está em _bootstrap/scripts/, vault é 2 níveis acima
VAULT="${VAULT:-$(cd "$(dirname "$0")"/../.. && pwd)}"

PROMPT_LOG="$VAULT/_memory/.prompt-log.txt"
FLAG="$VAULT/_memory/.consolidation-ready"
LOG="$VAULT/_memory/activity-log.md"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M')
THRESHOLD=30  # mínimo de prompts para valer a análise

mkdir -p "$VAULT/_memory"

# Nenhum log ainda — nada a fazer
if [ ! -f "$PROMPT_LOG" ]; then
  echo "[$TIMESTAMP] weekly-prompt-consolidation: sem log de prompts ainda, pulando."
  exit 0
fi

PROMPT_COUNT=$(wc -l < "$PROMPT_LOG" | tr -d ' ')

if [ "${PROMPT_COUNT:-0}" -lt "$THRESHOLD" ]; then
  echo "[$TIMESTAMP] weekly-prompt-consolidation: $PROMPT_COUNT prompts acumulados (threshold: $THRESHOLD). Aguardando mais dados."
  exit 0
fi

# Gerar estatísticas básicas (sem LLM) para enriquecer o contexto da análise
SLASH_COUNT=$(grep -cE '^\[.*\] /' "$PROMPT_LOG" 2>/dev/null || echo 0)
TOP_CMDS=$(grep -oE '^\[.*\] /[a-z-]+' "$PROMPT_LOG" 2>/dev/null | \
           grep -oE '/[a-z-]+' | sort | uniq -c | sort -rn | head -5 | \
           awk '{printf "  %s × %s\n", $1, $2}')
UNIQUE_CWDS=$(grep -oE 'cwd:[^]]+' "$PROMPT_LOG" 2>/dev/null | sort -u | wc -l | tr -d ' ')

# Salvar resumo estrutural junto com o log para o skill usar
STATS_FILE="$VAULT/_memory/.prompt-log-stats.txt"
cat > "$STATS_FILE" << EOF
Gerado: $TIMESTAMP
Total de prompts: $PROMPT_COUNT
Slash commands: $SLASH_COUNT
Projetos distintos (cwd): $UNIQUE_CWDS
Top slash commands:
$TOP_CMDS
EOF

# Criar flag — hook exibirá aviso no próximo prompt
touch "$FLAG"

# Registrar no activity log
[ -f "$LOG" ] && \
  printf '\n## [%s] cron | weekly-prompt-consolidation — %s prompts prontos para analise\n' \
    "$TIMESTAMP" "$PROMPT_COUNT" >> "$LOG"

echo "[$TIMESTAMP] weekly-prompt-consolidation: $PROMPT_COUNT prompts acumulados. Flag criada — aviso aparecerá no próximo prompt."

if [ -x "$VAULT/.claude/scripts/sb-agent-learn.sh" ]; then
  export VAULT
  bash "$VAULT/.claude/scripts/sb-agent-learn.sh" --trigger weekly || true
fi
