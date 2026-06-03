#!/usr/bin/env bash
# git-backlink-harvester.sh — anota padrões tocados em commits do dia em work-log.md.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$VAULT_ROOT"
exec python3 "$SCRIPT_DIR/lib/git_backlink_harvester.py" "$@"
