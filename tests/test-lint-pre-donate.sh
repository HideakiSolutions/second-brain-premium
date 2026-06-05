#!/bin/bash
# Smoke test do lint-pre-donate.sh: confirmar que detecta violacao em
# input contaminado e passa em input limpo.
set -u
cd "$(dirname "$0")/.." || exit 2

LINT=".claude/scripts/lint-pre-donate.sh"
[ -x "$LINT" ] || { echo "FAIL: $LINT nao executavel"; exit 1; }

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

# Caso 1: input limpo deve retornar exit 0
cat > "$TMP/clean.md" <<'EOF'
---
tags: [example, public]
status: active
---
# Clean
Texto agnostico publico.
EOF

if ! bash "$LINT" "$TMP/clean.md" >/dev/null; then
  echo "FAIL: input limpo retornou exit nao-zero"
  exit 1
fi

# Caso 2: input com IP privado deve retornar exit 1
cat > "$TMP/dirty.md" <<'EOF'
---
tags: [test]
---
# Dirty
Host: 192.168.1.10
EOF

if bash "$LINT" "$TMP/dirty.md" >/dev/null 2>&1; then
  echo "FAIL: input contaminado passou (deveria ter retornado 1)"
  exit 1
fi

echo "OK: lint-pre-donate detecta violacoes e aceita inputs limpos"
exit 0
