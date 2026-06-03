#!/bin/bash
# Hook: UserPromptSubmit
# 1. Registra todo prompt em _memory/.prompt-log.txt (sempre, sem filtro)
# 2. Injeta state.md do projeto ativo (uma vez por dia por projeto)
# 3. Injeta alertas de pendências (uma vez por dia por projeto)
#
# Registrado em ~/.claude/settings.json pelo install.sh:
#   "UserPromptSubmit": [{ "hooks": [{ "type": "command",
#     "command": "bash {VAULT}/_bootstrap/global/hooks/on-prompt-submit.sh", "timeout": 5 }] }]

# CRÍTICO: stdin só pode ser lido uma vez — deve ser a primeira operação
INPUT=$(cat)
PROMPT=$(echo "$INPUT" | jq -r '.prompt // empty' 2>/dev/null || echo "")
CWD=$(echo "$INPUT" | jq -r '.cwd // empty' 2>/dev/null || echo "$PWD")

# Auto-detectar vault: script está em _bootstrap/global/hooks/, vault é 3 níveis acima
VAULT="${VAULT:-$(cd "$(dirname "$0")"/../.. && pwd)}"
PROMPT_LOG="$VAULT/_memory/.prompt-log.txt"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M')

# Garantir que _memory/ existe
mkdir -p "$VAULT/_memory"

# Gravar prompt no log (sempre — dotfile, não indexado no vault)
if [ -n "$PROMPT" ]; then
  printf '[%s|cwd:%s] %s\n' "$TIMESTAMP" "${CWD##*/}" "$PROMPT" >> "$PROMPT_LOG"
fi

# Hooks assistidos v1: advisory-first. Eles podem orientar e enfileirar
# capturas, mas nao alteram notas duraveis do vault.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
printf '%s' "$INPUT" | bash "$SCRIPT_DIR/secret-leak-guard.sh" prompt || true
printf '%s' "$INPUT" | bash "$SCRIPT_DIR/continue-contract.sh" || true
printf '%s' "$INPUT" | bash "$SCRIPT_DIR/validation-tier-suggest.sh" || true
printf '%s' "$INPUT" | bash "$SCRIPT_DIR/post-merge-recorder.sh" || true

# Verificar se há alerta de consolidação pendente
CONSOLIDATION_FLAG="$VAULT/_memory/.consolidation-ready"
if [ -f "$CONSOLIDATION_FLAG" ]; then
  PROMPT_COUNT=$(wc -l < "$PROMPT_LOG" 2>/dev/null || echo 0)
  printf '[VAULT] %s prompts acumulados para analise. Execute /consolidate-prompts para identificar padroes e candidatos a skills/commands/hooks.\n' "$PROMPT_COUNT"
  rm -f "$CONSOLIDATION_FLAG"
fi

# Verificar auto-captures pendentes (Fase B)
AUTO_INBOX="$VAULT/_pipeline/inbox"
if [ -d "$AUTO_INBOX" ]; then
  PENDING_FILES=$(find "$AUTO_INBOX" -maxdepth 1 -name 'auto-captures-*.md' 2>/dev/null | wc -l)
  if [ "$PENDING_FILES" -gt 0 ]; then
    PENDING_EVENTS=$(grep -c "^## \[" "$AUTO_INBOX"/auto-captures-*.md 2>/dev/null | awk -F: '{ s += $NF } END { print s+0 }')
    if [ "$PENDING_EVENTS" -gt 0 ]; then
      printf '[VAULT] %s auto-captures pendentes em _pipeline/inbox/. Execute /review-captures para promover ou descartar.\n' "$PENDING_EVENTS"
    fi
  fi
fi

# Guard: alertas e injeção de state apenas uma vez por dia por projeto
ALERTED_TODAY="/tmp/claude-vault-alerted-$(date +%Y%m%d)-${PWD##*/}"
if [ -f "$ALERTED_TODAY" ]; then
  exit 0
fi
touch "$ALERTED_TODAY"

# Injetar state.md do projeto ativo (uma vez por dia por projeto)
PROJECT_NAME="${CWD##*<projects-root>/}"
PROJECT_NAME="${PROJECT_NAME%%/*}"
STATE_FILE="$VAULT/_knowledge/projects/${PROJECT_NAME}/state.md"
STATE_INJECTED_FLAG="/tmp/claude-state-injected-$(date +%Y%m%d)-${PROJECT_NAME}"

if [ -f "$STATE_FILE" ] && [ ! -f "$STATE_INJECTED_FLAG" ]; then
  touch "$STATE_INJECTED_FLAG"
  STATE_CONTENT=$(grep -v "^---" "$STATE_FILE" | grep -v "^updated:" | sed '/^[[:space:]]*$/d')
  printf '[PROJETO: %s]\n%s\n' "$PROJECT_NAME" "$STATE_CONTENT"
fi

# Verificar pendências e injetar alertas
# ESCOPO: estas pendências são VAULT-WIDE (cross-project), derivadas de flags
# globais em _memory/ e do rollup de portfólio current-state.md. NÃO são, e não
# devem ser tratadas como, atividades do projeto ativo (PROJECT_NAME acima).
# São AWARENESS ambient — o agente não deve pivotar o trabalho para elas nem
# misturá-las com o backlog do projeto. Ver CLAUDE.md "Project scope discipline".
NEEDS_END="$VAULT/_memory/.needs-end-session"
COMPACTED="$VAULT/_memory/.compacted-without-end-session"
STATE="$VAULT/_memory/current-state.md"
ALERTS=""

[ -f "$NEEDS_END" ] && \
  ALERTS="${ALERTS}\n- Sessao anterior ($(cat "$NEEDS_END" 2>/dev/null)) encerrada sem /end-session."

[ -f "$COMPACTED" ] && \
  ALERTS="${ALERTS}\n- Compactacao sem /end-session previo: $(cat "$COMPACTED" 2>/dev/null)."

if [ -f "$STATE" ]; then
  LAST=$(grep "^updated:" "$STATE" 2>/dev/null | sed 's/updated: //' | tr -d ' ')
  if [ -n "$LAST" ]; then
    LAST_TS=$(date -d "$LAST" +%s 2>/dev/null || echo 0)
    NOW_TS=$(date +%s)
    DAYS=$(( (NOW_TS - ${LAST_TS:-$NOW_TS}) / 86400 ))
    [ "${DAYS:-0}" -gt 3 ] && \
      ALERTS="${ALERTS}\n- current-state.md desatualizado ha ${DAYS} dias (ultima atualizacao: ${LAST})."
  fi
fi

# Verificar promotion-backlog (módulo opcional)
BACKLOG="$VAULT/_cores/promotion-backlog.md"
BACKLOG_ALERTED="/tmp/claude-vault-backlog-alerted-$(date +%Y%m%d)-${PWD##*/}"
if [ -f "$BACKLOG" ] && [ ! -f "$BACKLOG_ALERTED" ]; then
  CANDIDATE_COUNT=$(grep -c "| candidato |" "$BACKLOG" 2>/dev/null || echo 0)
  LAST_REVIEW=$(grep "^> Última varredura" "$BACKLOG" 2>/dev/null | tail -1 | sed 's/.*: //')
  if [ "${CANDIDATE_COUNT:-0}" -gt 0 ] && [ -n "$LAST_REVIEW" ]; then
    LAST_TS=$(date -d "$LAST_REVIEW" +%s 2>/dev/null || echo 0)
    NOW_TS=$(date +%s)
    BACKLOG_DAYS=$(( (NOW_TS - ${LAST_TS:-$NOW_TS}) / 86400 ))
    if [ "${BACKLOG_DAYS:-0}" -gt 7 ]; then
      touch "$BACKLOG_ALERTED"
      ALERTS="${ALERTS}\n- Core promotion-backlog tem ${CANDIDATE_COUNT} candidato(s) nao revisado(s) ha ${BACKLOG_DAYS} dias. Execute /core-session para analisar."
    fi
  fi
fi

# Verificar contexto de infra no prompt (usa $PROMPT lido do stdin)
SNAPSHOT="$VAULT/_infrastructure/SNAPSHOT.md"
if echo "$PROMPT" | grep -qiE "192\.168\.|kubectl|namespace|argocd|gitops|deploy|cluster|k8s|kubernetes|vault|redis|kafka|postgres"; then
  if [ -f "$SNAPSHOT" ]; then
    SNAP_DATE=$(grep "^updated:" "$SNAPSHOT" 2>/dev/null | sed 's/updated: //' | tr -d ' ')
    SNAP_TS=$(date -d "${SNAP_DATE:-1970-01-01}" +%s 2>/dev/null || echo 0)
    NOW_TS=$(date +%s)
    SNAP_DAYS=$(( (NOW_TS - SNAP_TS) / 86400 ))
    [ "${SNAP_DAYS:-0}" -gt 1 ] && \
      ALERTS="${ALERTS}\n- [INFRA] Snapshot de infraestrutura desatualizado ha ${SNAP_DAYS} dias. Consulte _infrastructure/SNAPSHOT.md ou rode infra-snapshot.sh."
  else
    ALERTS="${ALERTS}\n- [INFRA] Snapshot de infraestrutura nao existe ainda. Consulte _infrastructure/ para documentacao estatica."
  fi
fi

[ -z "$ALERTS" ] && exit 0

# Banner explícito de escopo: estas pendências são cross-vault (ambient), NÃO do
# projeto ativo. O agente deve tratá-las como awareness e não pivotar o trabalho.
printf '[VAULT][ambient — cross-vault, NÃO é escopo do projeto ativo] Pendencias detectadas:%b\nAwareness apenas. Execute /end-session quando quiser sincronizar — não pivote a tarefa atual por causa disto.\n' "$ALERTS"
