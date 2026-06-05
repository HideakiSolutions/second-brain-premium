#!/bin/bash
# Common agent observational learn surface.
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT="${VAULT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
export VAULT VAULT_ROOT="${VAULT_ROOT:-$VAULT}"

if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
else
  PYTHON=python
fi

exec "$PYTHON" "$SCRIPT_DIR/lib/memory_reviewer.py" learn "$@"
