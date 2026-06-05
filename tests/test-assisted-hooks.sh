#!/bin/bash
# Simula cenarios assistidos sem depender do Claude runtime.
set -u
cd "$(dirname "$0")/.." || exit 2

CONTINUE_OUT=$(printf '%s' '{"prompt":"pode prosseguir e implement the plan","cwd":"/tmp/proj"}' | bash .claude/scripts/continue-contract.sh)
echo "$CONTINUE_OUT" | grep -q "Contrato de continuidade" || { echo "FAIL: ContinueContract nao orientou"; exit 1; }

TIER_OUT=$(printf '%s' '{"prompt":"validar deploy gitops argocd rollout url publica","cwd":"/tmp/proj"}' | bash .claude/scripts/validation-tier-suggest.sh)
echo "$TIER_OUT" | grep -q "Gate sugerido: live" || { echo "FAIL: ValidationTierSuggest nao sugeriu live"; exit 1; }

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/_memory"
cat > "$TMP/_memory/.prompt-log.txt" <<'EOF'
[2026-05-11 00:00] /focus projeto
[2026-05-11 00:01] Process exited with code 0
[2026-05-11 00:02] validar merge sem copiar prompt bruto
EOF
SANITIZED=$(bash .claude/scripts/prompt-log-sanitizer.sh "$TMP/_memory/.prompt-log.txt")
echo "$SANITIZED" | grep -q "command:/focus" || { echo "FAIL: sanitizer perdeu slash command"; exit 1; }
if echo "$SANITIZED" | grep -q "copiar prompt bruto\\|Process exited"; then
  echo "FAIL: sanitizer vazou texto bruto"
  exit 1
fi

TODAY=$(date '+%Y-%m-%d')
INBOX="$TMP/_pipeline/inbox/auto-captures-$TODAY.md"
mkdir -p "$TMP/_pipeline/inbox"
printf '%s' '{"prompt":"merge PR #123 e tag v1.2.3","cwd":"/tmp/assisted-hooks"}' | VAULT="$TMP" bash .claude/scripts/post-merge-recorder.sh >/tmp/post-merge-recorder.out
if ! grep -q "post-merge-recorder" "$INBOX" 2>/dev/null; then
  echo "FAIL: PostMergeRecorder nao criou captura"
  exit 1
fi

mkdir -p "$TMP/_knowledge/projects/assisted-hooks"
cat > "$TMP/_knowledge/projects/assisted-hooks/state.md" <<'EOF'
# Assisted Hooks
- Precedente: preflight deve consultar memoria antes de execucao.
EOF
PREFLIGHT_OUT=$(printf '%s' '{"prompt":"validar memoria antes de implementar","cwd":"/tmp/assisted-hooks","project":"assisted-hooks"}' | \
  SB_AGENT_OFFLINE=1 VAULT="$TMP" bash .claude/scripts/on-prompt-submit.sh)
echo "$PREFLIGHT_OUT" | grep -q "\[MEMORY\]" || { echo "FAIL: UserPromptSubmit nao chamou preflight"; exit 1; }

printf '%s' '{"hook_event_name":"PreCompact","cwd":"/tmp/assisted-hooks"}' | VAULT="$TMP" bash .claude/scripts/on-pre-compact.sh
grep -q "memory-reviewer | pre-compact" "$TMP/_memory/activity-log.md" || { echo "FAIL: PreCompact nao chamou sync"; exit 1; }

printf '%s' '{"hook_event_name":"SessionEnd","cwd":"/tmp/assisted-hooks"}' | VAULT="$TMP" bash .claude/scripts/on-session-end.sh
grep -q "memory-reviewer | session-end" "$TMP/_memory/activity-log.md" || { echo "FAIL: SessionEnd nao chamou sync"; exit 1; }

echo "OK: hooks assistidos simulados"
exit 0
