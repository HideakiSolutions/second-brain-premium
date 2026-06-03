#!/usr/bin/env bash
# style-profile.sh — regenera _bootstrap/agentic/style/fingerprint.json analisando _content/articles/.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$VAULT_ROOT"
exec python3 "$VAULT_ROOT/_bootstrap/agentic/style/profiler.py" "$@"
