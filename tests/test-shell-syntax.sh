#!/bin/bash
# Bash -n em todos os .sh do vault. Detecta erros de sintaxe sem executar.
set -u
cd "$(dirname "$0")/.." || exit 2

FAIL=0
SCRIPTS=$(find .claude/scripts tests -name "*.sh" -type f 2>/dev/null)

for s in $SCRIPTS; do
  if ! bash -n "$s" 2>&1; then
    echo "FAIL: $s"
    FAIL=$((FAIL + 1))
  fi
done

if [ $FAIL -eq 0 ]; then
  echo "OK: $(echo "$SCRIPTS" | wc -l) script(s) com sintaxe valida"
  exit 0
fi
echo "FAIL: $FAIL script(s) com erro de sintaxe"
exit 1
