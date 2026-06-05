#!/bin/bash
# Hook: PreCompact
# Executado antes da compactação de contexto do Claude Code.
# Responsabilidades:
#   1. Snapshot automático do contexto crítico (next steps + open questions)
#   2. Append no activity log
#   3. Preservar .pre-compact-notes.md se existir (manual ou gerado aqui)
#   4. Criar flag .compacted-without-end-session se /end-session não rodou
#
# Registrado em ~/.claude/settings.json pelo install.sh:
#   "PreCompact": [{ "hooks": [{ "type": "command",
#     "command": "bash {VAULT}/_bootstrap/global/hooks/on-pre-compact.sh", "timeout": 5 }] }]

# Auto-detectar vault: script está em _bootstrap/global/hooks/, vault é 3 níveis acima
VAULT="${VAULT:-$(cd "$(dirname "$0")"/../.. && pwd)}"

LOG="$VAULT/_memory/activity-log.md"
NOTES="$VAULT/_memory/.pre-compact-notes.md"
FLAG="$VAULT/_memory/.compacted-without-end-session"
STATE="$VAULT/_memory/current-state.md"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M')
TODAY=$(date '+%Y-%m-%d')

# Garantir que _memory/ existe
mkdir -p "$VAULT/_memory"

# --- Snapshot automático de contexto crítico ---
# Se não há notas manuais, extrair próximos passos e perguntas abertas do current-state
if [ ! -f "$NOTES" ] && [ -f "$STATE" ]; then
  NEXT_STEPS=$(awk '/^### Next Steps/{found=1; next} found && /^###/{exit} found{print}' "$STATE" | grep -v '^$' | head -5)
  OPEN_Q=$(awk '/^### Open Questions/{found=1; next} found && /^###/{exit} found{print}' "$STATE" | grep -v '^$' | head -3)
  if [ -n "$NEXT_STEPS" ] || [ -n "$OPEN_Q" ]; then
    {
      echo "# Snapshot pré-compactação — $TIMESTAMP"
      echo ""
      [ -n "$NEXT_STEPS" ] && printf "## Próximos Passos\n%s\n\n" "$NEXT_STEPS"
      [ -n "$OPEN_Q" ]    && printf "## Perguntas Abertas\n%s\n\n" "$OPEN_Q"
    } > "$NOTES"
  fi
fi

# Registrar no activity log
printf '\n## [%s] compact | contexto compactado\n' "$TIMESTAMP" >> "$LOG"

# Preservar notas (manuais ou geradas acima) no log e remover o arquivo
if [ -f "$NOTES" ]; then
  CONTENT=$(cat "$NOTES")
  printf '\n### Pre-compact notes\n%s\n' "$CONTENT" >> "$LOG"
  rm -f "$NOTES"
fi

# Criar flag se /end-session não rodou antes desta compactação
if ! grep -q "session-end | .*—" "$LOG" 2>/dev/null; then
  printf '%s\n' "$TODAY" > "$FLAG"
fi

VAULT="$VAULT" bash "$(dirname "$0")/sb-agent-sync.sh" \
  --runtime claude --cwd "$PWD" --trigger pre-compact --summary "contexto compactado" --event-id "$TIMESTAMP" >/dev/null 2>&1 || true

exit 0
