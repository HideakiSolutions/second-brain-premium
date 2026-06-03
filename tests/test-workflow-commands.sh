#!/bin/bash
# Verifica comandos canonicos do core workflow.
set -u
cd "$(dirname "$0")/.." || exit 2

COMMANDS=(
  "beacon"
  "completion-audit"
  "delivery-closeout"
  "live-deploy-validate"
  "ux-product-audit"
  "skill-evolve"
)

FAIL=0
for cmd in "${COMMANDS[@]}"; do
  file=".claude/commands/$cmd.md"
  if [ ! -f "$file" ]; then
    echo "FAIL: $file ausente"
    FAIL=$((FAIL + 1))
    continue
  fi
  grep -q "^## Descrição" "$file" || { echo "FAIL: $file sem descricao"; FAIL=$((FAIL + 1)); }
  grep -q "^## Argumentos" "$file" || { echo "FAIL: $file sem argumentos"; FAIL=$((FAIL + 1)); }
  grep -q "^## Regras" "$file" || { echo "FAIL: $file sem regras"; FAIL=$((FAIL + 1)); }
done

END_SESSION=".claude/commands/end-session.md"
DELIVERY_CLOSEOUT=".claude/commands/delivery-closeout.md"
grep -q "Fechamento de entrega e validação HSEOS/distribuível" "$END_SESSION" || { echo "FAIL: /end-session sem gate HSEOS/distribuivel"; FAIL=$((FAIL + 1)); }
grep -q "delivery-closeout" "$END_SESSION" || { echo "FAIL: /end-session sem delivery-closeout"; FAIL=$((FAIL + 1)); }
grep -q "ADR.*Proposed" "$END_SESSION" || { echo "FAIL: /end-session sem regra de ADR Proposed"; FAIL=$((FAIL + 1)); }
grep -q "Paridade Claude/Codex" "$END_SESSION" || { echo "FAIL: /end-session sem paridade Claude/Codex no output"; FAIL=$((FAIL + 1)); }
grep -q "vault:" "$END_SESSION" || { echo "FAIL: /end-session sem status vault"; FAIL=$((FAIL + 1)); }
grep -q "vault:" "$DELIVERY_CLOSEOUT" || { echo "FAIL: /delivery-closeout sem status vault"; FAIL=$((FAIL + 1)); }

if [ "$FAIL" -eq 0 ]; then
  echo "OK: comandos canonicos presentes"
  exit 0
fi
exit 1
