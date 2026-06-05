#!/bin/bash
# Hook: SessionEnd (project-scoped — dispara apenas dentro do vault)
# Responsabilidades:
#   1. Registrar session-end no activity log (sem duplicar o hook global)
#   2. Criar flag .needs-end-session para lembrar que /end-session não foi rodado
#   3. Atualizar campo updated no current-state.md
#   4. Atualizar snapshot de infra se sessão envolveu mudanças relacionadas
#
# Registrado em ~/.claude/settings.json pelo install.sh:
#   "SessionEnd": [{ "hooks": [{ "type": "command",
#     "command": "bash {VAULT}/_bootstrap/global/hooks/on-session-end.sh", "timeout": 5 }] }]

# Auto-detectar vault: script está em _bootstrap/global/hooks/, vault é 3 níveis acima
VAULT="${VAULT:-$(cd "$(dirname "$0")"/../.. && pwd)}"

LOG="$VAULT/_memory/activity-log.md"
STATE="$VAULT/_memory/current-state.md"
FLAG="$VAULT/_memory/.needs-end-session"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M')
TODAY=$(date '+%Y-%m-%d')

# Garantir que _memory/ existe
mkdir -p "$VAULT/_memory"

# Verificar se o último fechamento de sessão de hoje foi um /end-session real.
LATEST_SESSION_END=""
[ -f "$LOG" ] && LATEST_SESSION_END=$(grep "^\## \[$TODAY.*session-end | " "$LOG" 2>/dev/null | tail -1)

# Atualizar campo updated no current-state.md
if [ -f "$STATE" ]; then
  sed -i "s/^updated: .*/updated: $TODAY/" "$STATE"
fi

# Criar flag se /end-session não foi rodado desde o último encerramento.
if ! printf '%s' "$LATEST_SESSION_END" | grep -q "session-end | .*—"; then
  printf '%s\n' "$TODAY" > "$FLAG"
fi

# Registrar este encerramento de sessão do vault. Isso torna a próxima sessão
# pendente até um novo /end-session escrever uma linha de projeto.
printf '\n## [%s] session-end | vault\n' "$TIMESTAMP" >> "$LOG"

VAULT="$VAULT" bash "$(dirname "$0")/sb-agent-sync.sh" \
  --runtime claude --cwd "$PWD" --trigger session-end --summary "sessao encerrada" --event-id "$TIMESTAMP" >/dev/null 2>&1 || true

VAULT="$VAULT" bash "$(dirname "$0")/sb-semantic-index-flush.sh" --max-files "${SB_SEMANTIC_INDEX_FLUSH_MAX:-25}" >/dev/null 2>&1 || true

# Atualizar snapshot de infra se sessão envolveu mudanças relacionadas
TRANSCRIPT_FILE="/tmp/claude-session-transcript-${PWD##*/}"
if [ -f "$TRANSCRIPT_FILE" ] && grep -qiE "kubectl|argocd|namespace|deploy|gitops|k8s|kubernetes" "$TRANSCRIPT_FILE" 2>/dev/null; then
  bash "$(dirname "$0")/infra-snapshot.sh" 2>/dev/null &
fi

exit 0
