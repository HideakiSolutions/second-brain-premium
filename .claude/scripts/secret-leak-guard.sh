#!/bin/bash
# SecretLeakGuard: warning on prompts, blocking on sensitive writes.
set -u

MODE="${1:-prompt}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
  exit 0
fi

python3 "$SCRIPT_DIR/lib/workflow_assistant.py" secret-guard --mode "$MODE"
