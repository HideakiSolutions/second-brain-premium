#!/bin/bash
# Estrutura mínima do vault: pastas obrigatorias devem existir.
set -u
cd "$(dirname "$0")/.." || exit 2

REQUIRED_DIRS=(
  "_knowledge"
  "_knowledge/projects"
  "_knowledge/projects/_template"
  "_bootstrap"
  "_bootstrap/agentic"
  "_bootstrap/templates"
  "_bootstrap/git-hooks"
  "_prompts"
  ".claude/commands"
  ".claude/scripts"
  ".claude/skills"
  ".codex/skills"
  ".specs/decisions"
)

REQUIRED_FILES=(
  "AGENTS.md"
  "CLAUDE.md"
  "START-HERE.md"
  ".claude/settings.json"
  "pyproject.toml"
)

FAIL=0
for d in "${REQUIRED_DIRS[@]}"; do
  if [ ! -d "$d" ]; then
    echo "FAIL: pasta '$d' nao existe"
    FAIL=$((FAIL + 1))
  fi
done

for f in "${REQUIRED_FILES[@]}"; do
  if [ ! -f "$f" ]; then
    echo "FAIL: arquivo '$f' nao existe"
    FAIL=$((FAIL + 1))
  fi
done

if [ $FAIL -eq 0 ]; then
  echo "OK: estrutura completa (${#REQUIRED_DIRS[@]} dirs, ${#REQUIRED_FILES[@]} files)"
  exit 0
fi
exit 1
