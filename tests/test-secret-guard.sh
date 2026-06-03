#!/bin/bash
# Testa SecretLeakGuard com fixtures benignas e um padrao sintetico.
set -u
cd "$(dirname "$0")/.." || exit 2

GUARD=".claude/scripts/secret-leak-guard.sh"
[ -x "$GUARD" ] || { echo "FAIL: $GUARD ausente"; exit 1; }

BENIGN='{"tool_input":{"file_path":"_prompts/example.md","content":"api_key = \"redacted-placeholder-value\""}}'
if ! printf '%s' "$BENIGN" | bash "$GUARD" tool >/tmp/secret-guard-benign.out 2>&1; then
  echo "FAIL: fixture benigna bloqueada"
  cat /tmp/secret-guard-benign.out
  exit 1
fi

SYNTHETIC_VALUE="ghp_1234567890abc"
SYNTHETIC_VALUE="${SYNTHETIC_VALUE}defghijklmnopqrstuvwxyzABCD"
SYNTHETIC=$(printf '{"tool_input":{"file_path":"_prompts/leak.md","content":"token = \\"%s\\""}}' "$SYNTHETIC_VALUE")
if printf '%s' "$SYNTHETIC" | bash "$GUARD" tool >/tmp/secret-guard-block.out 2>&1; then
  echo "FAIL: secret sintetico nao foi bloqueado"
  exit 1
fi
grep -q "Escrita bloqueada" /tmp/secret-guard-block.out || { echo "FAIL: mensagem de bloqueio ausente"; exit 1; }

echo "OK: SecretLeakGuard bloqueia escrita sensivel e aceita placeholder"
exit 0
