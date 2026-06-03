#!/bin/bash
# ValidationTierSuggest: suggests quick/full/live validation gates.
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
  exit 0
fi

python3 "$SCRIPT_DIR/lib/workflow_assistant.py" validation-tier || true
