#!/bin/bash
# _knowledge/projects/_template/ deve ter os 8 arquivos canonicos +
# README de instrucoes de uso.
set -u
cd "$(dirname "$0")/.." || exit 2

TEMPLATE_DIR="_knowledge/projects/_template"
REQUIRED=(
  "README.md"
  "_template.md"
  "state.md"
  "modules.md"
  "decisions.md"
  "gotchas.md"
  "integrations.md"
  "roadmap.md"
  "work-log.md"
)

FAIL=0
for f in "${REQUIRED[@]}"; do
  if [ ! -f "$TEMPLATE_DIR/$f" ]; then
    echo "FAIL: $TEMPLATE_DIR/$f ausente"
    FAIL=$((FAIL + 1))
  fi
done

if [ $FAIL -eq 0 ]; then
  echo "OK: template canonico completo (${#REQUIRED[@]} arquivos)"
  exit 0
fi
exit 1
