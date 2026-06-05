#!/bin/bash
# lint-pre-donate.sh — guard de IP para doações privado → starter (OSS).
#
# Uso:
#   bash lint-pre-donate.sh <arquivo-ou-pasta> [<arquivo-ou-pasta> ...]
#   git diff --name-only main HEAD | xargs bash lint-pre-donate.sh
#
# Saída:
#   0 = limpo, doação pode prosseguir.
#   1 = violações detectadas (IP, nomes proprietários, stack pesada, paths absolutos).
#   2 = uso inválido.
#
# Referência: ADR _decisions/2026-05-07-relacao-starter-vs-privado.md.
# Inspirado em tests/test-no-proprietary-terms.sh do second-brain-starter.

set -u

if [ $# -eq 0 ]; then
  echo "Uso: $0 <arquivo-ou-pasta> [...]" >&2
  echo "Exemplo: $0 _bootstrap/agentic/curator/main.py" >&2
  exit 2
fi

# Lista de arquivos a lintar (expande pastas)
TARGETS=()
for arg in "$@"; do
  if [ -d "$arg" ]; then
    while IFS= read -r f; do TARGETS+=("$f"); done < <(find "$arg" -type f \( -name '*.md' -o -name '*.sh' -o -name '*.py' -o -name '*.js' -o -name '*.ts' -o -name '*.yml' -o -name '*.yaml' -o -name '*.json' \))
  elif [ -f "$arg" ]; then
    TARGETS+=("$arg")
  else
    echo "AVISO: '$arg' nao existe — ignorado" >&2
  fi
done

if [ ${#TARGETS[@]} -eq 0 ]; then
  echo "Nenhum arquivo elegivel para lint." >&2
  exit 2
fi

VIOLATIONS=0
REPORT=""

# --- 1. Path absoluto privado (bloqueante) ---
PATTERN_PATHS='/opt/hideakisolutions/'
for f in "${TARGETS[@]}"; do
  matches=$(grep -nH -F "$PATTERN_PATHS" "$f" 2>/dev/null || true)
  if [ -n "$matches" ]; then
    REPORT+="\n[BLOCK] Path privado absoluto em:\n$matches\n"
    VIOLATIONS=$((VIOLATIONS + 1))
  fi
done

# --- 2. Nomes de projeto interno / cliente (bloqueante) ---
INTERNAL_NAMES=(
  "cambio-real"
  "cryptor"
  "srm-asset"
  "poynt-hub"
  "event-platform"
  "events-platform"
  "enterprise-hseos"
  "ai-engineering-orchestrator"
  "agentic-chain"
  "mcp-factory"
  "platform-gitops"
  "n8n-automations"
  "axon-web"
  "specter-ai"
  "Hideaki Servicos"
  "Hideaki Solucoes"
  "hideakisolutions"
  "hideakiservicos"
)
for name in "${INTERNAL_NAMES[@]}"; do
  for f in "${TARGETS[@]}"; do
    matches=$(grep -niH -F "$name" "$f" 2>/dev/null || true)
    if [ -n "$matches" ]; then
      REPORT+="\n[BLOCK] Nome interno '$name' em:\n$matches\n"
      VIOLATIONS=$((VIOLATIONS + 1))
    fi
  done
done

# --- 3. Stack pesada premium (warn — destilar antes de doar) ---
HEAVY_STACK=(
  "qdrant"
  "falkordb"
  "ollama"
  "bge-m3"
  "secondbrain-mcp"
)
HEAVY_HITS=""
for term in "${HEAVY_STACK[@]}"; do
  for f in "${TARGETS[@]}"; do
    matches=$(grep -niH -F "$term" "$f" 2>/dev/null || true)
    if [ -n "$matches" ]; then
      HEAVY_HITS+="\n  - $term em $f"
    fi
  done
done
if [ -n "$HEAVY_HITS" ]; then
  REPORT+="\n[WARN] Stack pesada detectada — destilar para versao agnostica antes de doar:$HEAVY_HITS\n"
  VIOLATIONS=$((VIOLATIONS + 1))
fi

# --- 4. Hostnames / IPs internos (bloqueante) ---
PATTERN_HOSTS='\b(node-80|node-90|10\.0\.|192\.168\.)[a-zA-Z0-9.-]*'
for f in "${TARGETS[@]}"; do
  matches=$(grep -nHE "$PATTERN_HOSTS" "$f" 2>/dev/null || true)
  if [ -n "$matches" ]; then
    REPORT+="\n[BLOCK] Hostname/IP interno em:\n$matches\n"
    VIOLATIONS=$((VIOLATIONS + 1))
  fi
done

# --- 5. Frontmatter com tags internas (bloqueante para .md) ---
INTERNAL_TAGS_PATTERN='tags:.*\b(cambio-real|cryptor|srm-asset|poynt-hub|enterprise-hseos|ai-engineering-orchestrator|agentic-chain|mcp-factory|axon-web|specter-ai)\b'
for f in "${TARGETS[@]}"; do
  case "$f" in *.md)
    matches=$(grep -nHE "$INTERNAL_TAGS_PATTERN" "$f" 2>/dev/null || true)
    if [ -n "$matches" ]; then
      REPORT+="\n[BLOCK] Tag interna em frontmatter:\n$matches\n"
      VIOLATIONS=$((VIOLATIONS + 1))
    fi
  ;; esac
done

# --- Relatorio final ---
echo "lint-pre-donate.sh — escaneados: ${#TARGETS[@]} arquivo(s)"
if [ $VIOLATIONS -eq 0 ]; then
  echo "OK: nenhuma violacao detectada. Doacao pode prosseguir."
  exit 0
fi

echo ""
echo "VIOLACOES: $VIOLATIONS"
echo -e "$REPORT"
echo ""
echo "Doacao bloqueada. Ver ADR _decisions/2026-05-07-relacao-starter-vs-privado.md."
exit 1
