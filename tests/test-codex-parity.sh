#!/bin/bash
# Verifica paridade Claude/Codex para todos os comandos versionados.
set -u
cd "$(dirname "$0")/.." || exit 2

FAIL=0
COUNT=0

while IFS= read -r command_file; do
  cmd="$(basename "$command_file" .md)"
  skill=".codex/skills/sb-$cmd/SKILL.md"
  agent=".codex/skills/sb-$cmd/agents/openai.yaml"
  COUNT=$((COUNT + 1))

  [ -f "$skill" ] || { echo "FAIL: $skill ausente"; FAIL=$((FAIL + 1)); continue; }
  [ -f "$agent" ] || { echo "FAIL: $agent ausente"; FAIL=$((FAIL + 1)); }
  grep -q "name: sb-$cmd" "$skill" || { echo "FAIL: $skill com name incorreto"; FAIL=$((FAIL + 1)); }
  grep -q "source_command: \".claude/commands/$cmd.md\"" "$skill" || { echo "FAIL: $skill sem source_command canonico"; FAIL=$((FAIL + 1)); }
  grep -q "source_root:" "$skill" && { echo "FAIL: $skill ainda declara source_root"; FAIL=$((FAIL + 1)); }
  grep -q "_bootstrap/global/commands" "$skill" && { echo "FAIL: $skill ainda aponta para _bootstrap/global/commands"; FAIL=$((FAIL + 1)); }
done < <(find .claude/commands -maxdepth 1 -type f -name "*.md" | sort)

# Cross-check against the installed global Codex runtime ONLY when present.
# CI runners (and any machine without the global runtime installed) have no
# ~/.codex — skip the parity diff there instead of failing the suite.
GLOBAL_CODEX="${CODEX_HOME:-$HOME/.codex}/skills"
if [ -d "$GLOBAL_CODEX" ] && find "$GLOBAL_CODEX" -maxdepth 1 -type d -name "sb-*" | grep -q .; then
  while IFS= read -r skill_dir; do
    name="$(basename "$skill_dir")"
    if [ -d "$GLOBAL_CODEX/$name" ]; then
      diff -qr "$skill_dir" "$GLOBAL_CODEX/$name" >/dev/null || { echo "FAIL: runtime global diverge de $name"; FAIL=$((FAIL + 1)); }
    else
      echo "FAIL: runtime global ausente para $name"
      FAIL=$((FAIL + 1))
    fi
  done < <(find .codex/skills -maxdepth 1 -type d -name "sb-*" | sort)
else
  echo "SKIP: runtime global Codex sb-* ausente ($GLOBAL_CODEX) — parity diff ignorado"
fi

if [ "$FAIL" -eq 0 ]; then
  echo "OK: paridade Codex de $COUNT comando(s)"
  exit 0
fi
exit 1
