#!/bin/bash
# Valida fila incremental de indexacao semantica acionada por hooks.
set -u
cd "$(dirname "$0")/.." || exit 2

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/_memory" "$TMP/_knowledge/projects/sample" "$TMP/.claude/scripts"
cat > "$TMP/_knowledge/projects/sample/state.md" <<'EOF'
---
tags: [project, active, knowledge-mgmt]
status: active
---
# Sample

## Padrões Aplicados
- [[Pattern A]]
- [[Pattern B]]

- Conteudo indexavel.
EOF
printf '%s\n' 'prompt bruto nao deve entrar no indice' > "$TMP/_memory/.prompt-log.txt"
printf '%s\n' 'png' > "$TMP/image.png"

PAYLOAD=$(printf '%s' '{"tool_name":"Write","tool_input":{"file_path":"_knowledge/projects/sample/state.md"}}')
printf '%s' "$PAYLOAD" | VAULT="$TMP" bash .claude/scripts/on-post-tool-use.sh >/tmp/semantic-index-post-tool.out
QUEUE="$TMP/_memory/.semantic-index-queue"
[ -f "$QUEUE" ] || { echo "FAIL: PostToolUse nao criou fila semantica"; exit 1; }
grep -q '^_knowledge/projects/sample/state.md$' "$QUEUE" || { echo "FAIL: fila sem path esperado"; exit 1; }

ABS="$TMP/_knowledge/projects/sample/state.md"
printf '%s' "{\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$ABS\"}}" | \
  VAULT="$TMP" bash .claude/scripts/sb-semantic-index-queue.sh >/tmp/semantic-index-queue-abs.out
printf '%s' '{"tool_name":"Write","tool_input":{"file_path":"_memory/.prompt-log.txt"}}' | \
  VAULT="$TMP" bash .claude/scripts/sb-semantic-index-queue.sh >/tmp/semantic-index-queue-ignore.out
printf '%s' '{"tool_name":"Write","tool_input":{"file_path":"image.png"}}' | \
  VAULT="$TMP" bash .claude/scripts/sb-semantic-index-queue.sh >/tmp/semantic-index-queue-binary.out
[ "$(grep -c '^_knowledge/projects/sample/state.md$' "$QUEUE")" -eq 1 ] || { echo "FAIL: fila semantica nao deduplicou"; exit 1; }
if grep -q '_memory/.prompt-log.txt\|image.png' "$QUEUE"; then
  echo "FAIL: fila semantica aceitou arquivo ignorado"
  exit 1
fi

cat > "$TMP/.claude/scripts/sb-reindex.sh" <<'STUB'
#!/bin/bash
printf '%s\n' "$@" > "$VAULT/_memory/reindex-args.txt"
STUB
chmod +x "$TMP/.claude/scripts/sb-reindex.sh"
DRY=$(VAULT="$TMP" bash .claude/scripts/sb-semantic-index-flush.sh --dry-run)
echo "$DRY" | grep -q 'sb-reindex.sh --paths _knowledge/projects/sample/state.md' || { echo "FAIL: dry-run nao chamou --paths"; exit 1; }
VAULT="$TMP" bash .claude/scripts/sb-semantic-index-flush.sh >/tmp/semantic-index-flush.out
grep -q '^--paths$' "$TMP/_memory/reindex-args.txt" || { echo "FAIL: flush nao chamou reindex incremental"; exit 1; }
grep -q '^_knowledge/projects/sample/state.md$' "$TMP/_memory/reindex-args.txt" || { echo "FAIL: flush nao passou path enfileirado"; exit 1; }
[ ! -f "$QUEUE" ] || { echo "FAIL: flush nao limpou fila"; exit 1; }

echo "OK: semantic index queue incremental"
exit 0
