#!/bin/bash
# tests/run-all.sh — orquestrador da suite local + CI.
#
# Uso:
#   bash tests/run-all.sh           # roda tudo, exit 1 se qualquer suite falhar
#
# Sem dependencias externas alem de bash + grep + find. ShellCheck e Python
# tooling (ruff/mypy) sao chamados pelo workflow CI, nao aqui.

set -u
cd "$(dirname "$0")/.." || exit 2

PASSED=0
FAILED=0
FAILED_SUITES=""

run_suite() {
  local name="$1"
  local script="$2"
  echo ""
  echo "=== $name ==="
  if bash "$script"; then
    PASSED=$((PASSED + 1))
  else
    FAILED=$((FAILED + 1))
    FAILED_SUITES+=" $name"
  fi
}

run_suite "shell-syntax"        "tests/test-shell-syntax.sh"
run_suite "structure"            "tests/test-structure.sh"
run_suite "frontmatter"          "tests/test-frontmatter.sh"
run_suite "template-completeness" "tests/test-template-completeness.sh"
run_suite "lint-pre-donate"      "tests/test-lint-pre-donate.sh"
run_suite "learn-loop"           "tests/test-learn-loop.sh"
run_suite "workflow-commands"     "tests/test-workflow-commands.sh"
run_suite "codex-parity"          "tests/test-codex-parity.sh"
run_suite "secret-guard"          "tests/test-secret-guard.sh"
run_suite "agent-memory-reviewer" "tests/test-agent-memory-reviewer.sh"
run_suite "semantic-index-queue"  "tests/test-semantic-index-queue.sh"
run_suite "assisted-hooks"        "tests/test-assisted-hooks.sh"
run_suite "synapse"               "tests/test-synapse.sh"

echo ""
echo "=========================================="
echo "Passed: $PASSED  |  Failed: $FAILED"
if [ $FAILED -gt 0 ]; then
  echo "Failed suites:$FAILED_SUITES"
  exit 1
fi
exit 0
