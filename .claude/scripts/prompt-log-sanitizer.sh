#!/bin/bash
# PromptLogSanitizer: emits aggregate-safe prompt signals without raw prompt text.
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT="${1:-$VAULT/_memory/.prompt-log.txt}"

if ! command -v python3 >/dev/null 2>&1; then
  exit 0
fi

python3 "$SCRIPT_DIR/lib/workflow_assistant.py" sanitize-log "$INPUT"
