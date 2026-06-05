#!/bin/bash
# Smoke tests for common agent memory reviewer surfaces.
set -u
cd "$(dirname "$0")/.." || exit 2

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$TMP/_memory" "$TMP/_pipeline/inbox" "$TMP/_knowledge/projects/sample"
cat > "$TMP/_memory/current-state.md" <<'EOF'
---
updated: 2026-06-01
---
# Current State

### Next Steps
- Validar hooks de memoria antes do export.

### Open Questions
- Como manter capturas idempotentes?
EOF
cat > "$TMP/_knowledge/projects/sample/state.md" <<'EOF'
# Sample
- Precedente: hooks escrevem apenas inbox e memory.
EOF
cat > "$TMP/_memory/.prompt-log.txt" <<'EOF'
[2026-06-05 00:00|cwd:sample] /search memoria
[2026-06-05 00:01|cwd:sample] validar runtime sem copiar prompt bruto secreto
[2026-06-05 00:02|cwd:sample] merge PR #1
[2026-06-05 00:03|cwd:sample] deploy gitops
[2026-06-05 00:04|cwd:sample] ajustar hook agent cli
[2026-06-05 00:05|cwd:sample] test suite
[2026-06-05 00:06|cwd:sample] memory reviewer
[2026-06-05 00:07|cwd:sample] second brain
[2026-06-05 00:08|cwd:sample] validation
[2026-06-05 00:09|cwd:sample] command hook
EOF

OUT=$(printf '%s' '{"runtime":"codex","cwd":"/work/sample","intent":"validar hooks de memoria","project":"sample"}' | \
  SB_AGENT_OFFLINE=1 VAULT="$TMP" bash .claude/scripts/sb-agent-preflight.sh)
echo "$OUT" | grep -q "\[MEMORY\]" || { echo "FAIL: preflight nao retornou contexto"; exit 1; }
if echo "$OUT" | grep -q "copiar prompt bruto secreto"; then
  echo "FAIL: preflight vazou prompt bruto"
  exit 1
fi

if grep -q 'sb-agent-preflight.*PROMPT' .claude/scripts/on-prompt-submit.sh; then
  echo "FAIL: UserPromptSubmit passa prompt bruto por argv"
  exit 1
fi

PAYLOAD='{"runtime":"codex","cwd":"/work/sample","trigger":"pre-compact","summary":"validacao de memoria e hooks","event_id":"evt-1"}'
printf '%s' "$PAYLOAD" | VAULT="$TMP" bash .claude/scripts/sb-agent-sync.sh >/tmp/sb-agent-sync-1.out
printf '%s' "$PAYLOAD" | VAULT="$TMP" bash .claude/scripts/sb-agent-sync.sh >/tmp/sb-agent-sync-2.out
TODAY=$(date '+%Y-%m-%d')
CAPTURE="$TMP/_pipeline/inbox/auto-captures-$TODAY.md"
[ -f "$CAPTURE" ] || { echo "FAIL: sync nao criou captura"; exit 1; }
[ "$(grep -c "capture-id:" "$CAPTURE")" -eq 1 ] || { echo "FAIL: sync nao foi idempotente"; exit 1; }
printf '%s' '{"runtime":"codex","cwd":"/work/sample","trigger":"pre-compact","summary":"validacao de memoria e hooks","event_id":"evt-2"}' | \
  VAULT="$TMP" bash .claude/scripts/sb-agent-sync.sh >/tmp/sb-agent-sync-3.out
[ "$(grep -c "capture-id:" "$CAPTURE")" -eq 2 ] || { echo "FAIL: sync colapsou eventos distintos"; exit 1; }
grep -q "event-key: evt-1" "$CAPTURE" || { echo "FAIL: captura sem event-key"; exit 1; }
[ -f "$TMP/_memory/.compacted-without-end-session" ] || { echo "FAIL: sync nao criou flag pre-compact"; exit 1; }
grep -q "memory-reviewer | pre-compact" "$TMP/_memory/activity-log.md" || { echo "FAIL: activity-log nao atualizado"; exit 1; }
if grep -q "copiar prompt bruto secreto" "$CAPTURE"; then
  echo "FAIL: captura contem prompt bruto"
  exit 1
fi

ALLOWLIST=$(VAULT="$TMP" python3 .claude/scripts/lib/memory_reviewer.py self-check)
echo "$ALLOWLIST" | grep -q "_pipeline/inbox/" || { echo "FAIL: allowlist sem inbox"; exit 1; }
if echo "$ALLOWLIST" | grep -q ".claude/commands\\|.codex/skills\\|_decisions"; then
  echo "FAIL: allowlist permite alvo proibido"
  exit 1
fi

LEARN=$(VAULT="$TMP" bash .claude/scripts/sb-agent-learn.sh --trigger test)
echo "$LEARN" | grep -q "patches_applied=0" || { echo "FAIL: learn nao confirmou politica sem patches"; exit 1; }
[ -f "$TMP/_pipeline/self-improvement-candidates.md" ] || { echo "FAIL: learn nao gerou candidatos"; exit 1; }

FAIL_VAULT=$(mktemp -d)
mkdir -p "$FAIL_VAULT/.claude/scripts"
printf '%s\n' '#!/bin/bash' 'exit 7' > "$FAIL_VAULT/.claude/scripts/learn-loop.sh"
chmod +x "$FAIL_VAULT/.claude/scripts/learn-loop.sh"
if VAULT="$FAIL_VAULT" bash .claude/scripts/sb-agent-learn.sh --trigger fail >/tmp/sb-agent-learn-fail.out; then
  echo "FAIL: learn escondeu falha do learn-loop"
  exit 1
fi
grep -q "learn_failed=true" /tmp/sb-agent-learn-fail.out || { echo "FAIL: learn nao reportou falha"; exit 1; }
rm -rf "$FAIL_VAULT"

echo "OK: agent memory reviewer surfaces"
exit 0
