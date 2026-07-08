#!/usr/bin/env bash
# sb-synapse-activate.sh — registra ativacao sinaptica a partir do JSON de hook (stdin).
#
# Uso: printf '%s' "$HOOK_JSON" | sb-synapse-activate.sh <read|write>
# Barato e fail-soft: sai silenciosamente se nao ha path de nota do vault no payload.
set -eu

SOURCE="${1:-read}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT_ROOT="${VAULT_ROOT:-${VAULT:-$(cd "$SCRIPT_DIR/../.." && pwd)}}"
export VAULT_ROOT

command -v python3 >/dev/null 2>&1 || exit 0

# heredoc ocupa o stdin do python; o payload do hook viaja por env var
SB_HOOK_PAYLOAD="$(cat || true)"
export SB_HOOK_PAYLOAD

python3 - "$SOURCE" <<'PYEOF' || true
import json
import os
import sys
from pathlib import Path

source = sys.argv[1]
raw = os.environ.get("SB_HOOK_PAYLOAD", "")
if not raw.strip():
    sys.exit(0)
try:
    payload = json.loads(raw)
except json.JSONDecodeError:
    sys.exit(0)

vault = Path(os.environ["VAULT_ROOT"]).resolve()

paths = []
tool_input = payload.get("tool_input") or {}
for key in ("file_path", "path", "notebook_path"):
    v = tool_input.get(key)
    if isinstance(v, str):
        paths.append(v)
for key in ("file_paths", "paths"):
    v = tool_input.get(key)
    if isinstance(v, list):
        paths.extend(str(x) for x in v if isinstance(x, str))

vault_md = []
for p in paths:
    try:
        rp = Path(p).resolve()
        rel = rp.relative_to(vault)
    except (ValueError, OSError):
        continue
    if rp.suffix.lower() != ".md":
        continue
    head = rel.parts[0] if rel.parts else ""
    if head.startswith(".") or head in {"node_modules", "tests"}:
        continue
    vault_md.append(str(rp))

if not vault_md:
    sys.exit(0)

sys.path.insert(0, str(vault / "_bootstrap" / "agentic" / "synapse"))
try:
    import physiology
    physiology.activate(vault_md, source, session=payload.get("session_id"))
except Exception:
    sys.exit(0)
PYEOF
