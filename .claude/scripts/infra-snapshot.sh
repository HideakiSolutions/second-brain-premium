#!/bin/bash
# Gera snapshot automatico da infraestrutura no second-brain.
# Chamado pelo on-session-end.sh quando sessao envolve mudancas de infra.

# Auto-detectar vault
VAULT="${VAULT:-$(cd "$(dirname "$0")"/../.. && pwd)}"
SNAPSHOT="$VAULT/_infrastructure/SNAPSHOT.md"
DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

{
  echo "---"
  echo "tags: [infrastructure, snapshot, auto-generated]"
  echo "status: active"
  echo "updated: $(date +%Y-%m-%d)"
  echo "---"
  echo ""
  echo "# Infrastructure Snapshot"
  echo ""
  echo "> Gerado automaticamente em $DATE"
  echo "> Nao editar manualmente — sera sobrescrito."
  echo ""

  echo "## Kubernetes Nodes"
  echo '```'
  kubectl get nodes -o wide 2>/dev/null || echo "(cluster inalcancavel)"
  echo '```'
  echo ""

  echo "## Resource Pressure"
  echo '```'
  kubectl top nodes 2>/dev/null || echo "(metrics-server indisponivel)"
  echo '```'
  echo ""

  echo "## Namespaces"
  echo '```'
  kubectl get namespaces 2>/dev/null || echo "(cluster inalcancavel)"
  echo '```'
  echo ""

  echo "## ArgoCD Applications"
  echo '```'
  kubectl get applications -n argocd -o wide 2>/dev/null || echo "(argocd inalcancavel)"
  echo '```'
  echo ""

  echo "## Pods com Problema"
  echo '```'
  kubectl get pods -A --field-selector='status.phase!=Running' 2>/dev/null | grep -v "Completed" || echo "(todos os pods em Running ou Completed)"
  echo '```'
} > "$SNAPSHOT"

exit 0
