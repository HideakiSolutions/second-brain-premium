#!/bin/bash
# Smoke test for the observational learn-loop.
set -u
cd "$(dirname "$0")/.." || exit 2

SCRIPT=".claude/scripts/learn-loop.sh"
[ -f "$SCRIPT" ] || { echo "FAIL: $SCRIPT ausente"; exit 1; }

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$TMP/_memory" "$TMP/_pipeline"

cat > "$TMP/_memory/.prompt-log.txt" <<'EOF'
[2026-05-11 00:00] /focus cwd:/tmp/project
[2026-05-11 00:01] validar ambiente global e projeto
[2026-05-11 00:02] verificar HSEOS Axon RTK MCP
[2026-05-11 00:03] commit push merge branch
[2026-05-11 00:04] second brain skill command hook agent
[2026-05-11 00:05] revalidar funcionamento do ambiente
[2026-05-11 00:06] compatibilidade Codex Claude skill
[2026-05-11 00:07] commit e merge
[2026-05-11 00:08] evoluir skills e comandos com base em interacoes
[2026-05-11 00:09] verificar repositorio limpo
[2026-05-11 00:10] Chunk ID: tool output ruidoso que deve sumir
[2026-05-11 00:11] stdout local com texto bruto que deve sumir
EOF

cat > "$TMP/_memory/activity-log.md" <<'EOF'
## [2026-05-11 00:00] focus | projeto analisado
## [2026-05-11 00:01] lint | validacao executada
## [2026-05-11 00:02] pipeline | painel atualizado
EOF

VAULT="$TMP" bash "$SCRIPT" >/dev/null

OUT="$TMP/_pipeline/self-improvement-candidates.md"
[ -f "$OUT" ] || { echo "FAIL: output nao criado"; exit 1; }

grep -q "Self-Improvement Candidates" "$OUT" || { echo "FAIL: titulo ausente"; exit 1; }
grep -q "Formalizar evolucao assistida" "$OUT" || { echo "FAIL: candidato de evolucao ausente"; exit 1; }
grep -q "Conteudo bruto de prompts permanece efemero" "$OUT" || { echo "FAIL: politica de prompt ausente"; exit 1; }
grep -q "Linhas sanitizadas usadas na analise" "$OUT" || { echo "FAIL: metrica sanitizada ausente"; exit 1; }
if grep -q "tool output ruidoso\\|texto bruto que deve sumir" "$OUT"; then
  echo "FAIL: output copiou prompt bruto ruidoso"
  exit 1
fi

echo "OK: learn-loop gera candidatos observacionais"
exit 0
