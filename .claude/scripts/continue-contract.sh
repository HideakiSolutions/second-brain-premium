#!/bin/bash
# ContinueContract: advisory continuation contract for explicit proceed prompts.
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
  exit 0
fi

python3 "$SCRIPT_DIR/lib/workflow_assistant.py" continue-contract || true
