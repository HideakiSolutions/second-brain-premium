#!/bin/bash
# PostMergeRecorder: records assisted PR/merge/tag captures in _pipeline/inbox.
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
  exit 0
fi

python3 "$SCRIPT_DIR/lib/workflow_assistant.py" post-merge-recorder || true
