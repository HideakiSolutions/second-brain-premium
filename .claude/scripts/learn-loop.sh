#!/bin/bash
# learn-loop.sh — observability-first self-improvement loop for the vault.
#
# Reads ephemeral interaction signals and emits governed improvement candidates.
# It never edits skills, commands, hooks, or raw prompt logs.

set -u

VAULT="${VAULT:-$(cd "$(dirname "$0")"/../.. && pwd)}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MEMORY_DIR="$VAULT/_memory"
PIPELINE_DIR="$VAULT/_pipeline"
PROMPT_LOG="$MEMORY_DIR/.prompt-log.txt"
SANITIZER="$VAULT/.claude/scripts/prompt-log-sanitizer.sh"
if [ ! -x "$SANITIZER" ]; then
  SANITIZER="$SCRIPT_DIR/prompt-log-sanitizer.sh"
fi
ACTIVITY_LOG="$MEMORY_DIR/activity-log.md"
GRAPH_METRICS="$MEMORY_DIR/graph-metrics.md"
OUTPUT="${OUTPUT:-$PIPELINE_DIR/self-improvement-candidates.md}"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M')

mkdir -p "$MEMORY_DIR" "$PIPELINE_DIR"

count_matches() {
  local pattern="$1"
  local file="$2"
  local matches
  if [ ! -f "$file" ]; then
    echo 0
    return
  fi
  matches=$(grep -Eic "$pattern" "$file" 2>/dev/null || true)
  echo "${matches:-0}"
}

prompt_count=0
if [ -f "$PROMPT_LOG" ]; then
  prompt_count=$(wc -l < "$PROMPT_LOG" | tr -d ' ')
fi

SANITIZED_PROMPT_LOG=$(mktemp)
trap 'rm -f "$SANITIZED_PROMPT_LOG"' EXIT
if [ -x "$SANITIZER" ]; then
  bash "$SANITIZER" "$PROMPT_LOG" > "$SANITIZED_PROMPT_LOG" 2>/dev/null || true
elif [ -f "$PROMPT_LOG" ]; then
  # Fallback conservador: nao copiar prompts brutos se o sanitizador falhar.
  : > "$SANITIZED_PROMPT_LOG"
fi

activity_count=0
if [ -f "$ACTIVITY_LOG" ]; then
  activity_count=$(grep -cE '^## \[[0-9]{4}-[0-9]{2}-[0-9]{2}' "$ACTIVITY_LOG" 2>/dev/null || echo 0)
fi

slash_count=$(count_matches 'command:/[a-z0-9-]+' "$SANITIZED_PROMPT_LOG")
commit_flow_count=$(count_matches 'category:git' "$SANITIZED_PROMPT_LOG")
validation_flow_count=$(count_matches 'category:validation' "$SANITIZED_PROMPT_LOG")
environment_flow_count=$(count_matches 'category:environment' "$SANITIZED_PROMPT_LOG")
second_brain_flow_count=$(count_matches 'category:second_brain' "$SANITIZED_PROMPT_LOG")

top_prompt_commands=""
if [ -f "$SANITIZED_PROMPT_LOG" ]; then
  top_prompt_commands=$(grep -oE 'command:/[a-z0-9-]+' "$SANITIZED_PROMPT_LOG" 2>/dev/null | \
    sed 's/^command://' | sort | uniq -c | sort -rn | head -10 | \
    awk '{printf "- %s: %s usos\n", $2, $1}')
fi
[ -n "$top_prompt_commands" ] || top_prompt_commands="- Nenhum slash command detectado no log efemero."

top_activity_commands=""
if [ -f "$ACTIVITY_LOG" ]; then
  top_activity_commands=$(grep -oE '^## \[[^]]+\] [a-z0-9-]+' "$ACTIVITY_LOG" 2>/dev/null | \
    sed -E 's/^## \[[^]]+\] //' | sort | uniq -c | sort -rn | head -10 | \
    awk '{printf "- %s: %s registros\n", $2, $1}')
fi
[ -n "$top_activity_commands" ] || top_activity_commands="- Nenhum comando detectado no activity log."

graph_summary="- Sem graph metrics disponivel."
if [ -f "$GRAPH_METRICS" ]; then
  graph_summary=$(grep -E 'Ilhas|Broken|broken|Tags|tags|Cobertura|coverage|Grau|grau|Arquivos|arquivos' "$GRAPH_METRICS" 2>/dev/null | head -12 | sed 's/^/- /')
  [ -n "$graph_summary" ] || graph_summary="- Graph metrics existe, mas nao contem indicadores reconhecidos."
fi

{
  cat <<EOF
# Self-Improvement Candidates

Gerado: $TIMESTAMP

Este arquivo e gerado pelo loop observacional \`learn-loop\`. Ele consolida sinais agregados de uso e propoe melhorias candidatas para revisao humana. Nao inclui conteudo bruto de prompts.

## Sinais Agregados

- Prompts efemeros analisados: $prompt_count
- Linhas sanitizadas usadas na analise: $(wc -l < "$SANITIZED_PROMPT_LOG" | tr -d ' ')
- Entradas no activity log: $activity_count
- Slash commands em prompts: $slash_count
- Sinais de fluxo Git/release: $commit_flow_count
- Sinais de validacao/revalidacao: $validation_flow_count
- Sinais de ambiente/paridade: $environment_flow_count
- Sinais de second-brain/skills/hooks/agentes: $second_brain_flow_count

## Metodo Sanitizado

- O log bruto permanece apenas em \`_memory/.prompt-log.txt\`.
- A analise usa somente categorias agregadas emitidas por \`PromptLogSanitizer\`.
- Ruido de tool output, compactacao, task notifications, stdout local e prompts de agente gerados e descartado antes da contagem.

## Top Slash Commands no Log Efemero

$top_prompt_commands

## Top Registros no Activity Log

$top_activity_commands

## Saude do Grafo

$graph_summary

## Candidatos

EOF

  if [ "$prompt_count" -lt 10 ] && [ "$activity_count" -lt 10 ]; then
    cat <<EOF
### Sem dados suficientes

**Tipo:** observacao
**Evidencia:** menos de 10 prompts e menos de 10 entradas de activity log.
**Proposta:** aguardar mais interacoes antes de propor mudancas em skills, comandos ou hooks.
**Status recomendado:** aguardando-dados

EOF
  fi

  if [ "$second_brain_flow_count" -ge 3 ]; then
    cat <<EOF
### Formalizar evolucao assistida de skills/comandos

**Tipo:** skill/command
**Frequencia:** $second_brain_flow_count
**Risco:** medio
**Prioridade:** alta se revisao humana aprovar
**Evidencia agregada:** $second_brain_flow_count sinal(is) relacionados a second-brain, skills, comandos, hooks ou agentes.
**Proposta:** manter este \`learn-loop\` como etapa observacional e criar, em fase posterior, um \`skill-evolve\` que transforme candidatos aprovados em patches.
**Arquivos provaveis:** \`.claude/commands/*\`, \`.codex/skills/sb-*/SKILL.md\`, hooks e scripts relacionados.
**Gates obrigatorios:** revisao humana, paridade Claude/Codex, secret scan, \`tests/run-all.sh\`.
**Status recomendado:** proposto

EOF
  fi

  if [ "$validation_flow_count" -ge 3 ]; then
    cat <<EOF
### Padronizar revalidacao de ambiente

**Tipo:** command
**Frequencia:** $validation_flow_count
**Risco:** baixo
**Prioridade:** media
**Evidencia agregada:** $validation_flow_count sinal(is) sobre validar, revalidar, testar, verificar funcionamento ou limpar estado.
**Proposta:** criar ou reforcar comando de revalidacao que rode checks de HSEOS, Axon, RTK, MCPs ativos, skills, hooks, agentes e paridade global/projeto.
**Gates obrigatorios:** saida resumida, lista de falhas acionaveis, sem modificar ambiente por padrao.
**Status recomendado:** proposto

EOF
  fi

  if [ "$environment_flow_count" -ge 3 ]; then
    cat <<EOF
### Consolidar provedor global de contexto operacional

**Tipo:** config/command
**Frequencia:** $environment_flow_count
**Risco:** medio
**Prioridade:** media
**Evidencia agregada:** $environment_flow_count sinal(is) sobre ambiente global, projeto, Codex, Claude, HSEOS, Axon, RTK ou MCPs.
**Proposta:** expor o second-brain como provedor comum de conhecimento operacional via CLI/MCP, evitando duplicacao por projeto e preservando overrides locais quando necessarios.
**Gates obrigatorios:** nao duplicar estado, documentar precedencia global vs projeto, smoke test a partir de repos diferentes.
**Status recomendado:** proposto

EOF
  fi

  if [ "$commit_flow_count" -ge 3 ]; then
    cat <<EOF
### Separar fluxo de merge de fluxo de aprendizado

**Tipo:** hook/command
**Frequencia:** $commit_flow_count
**Risco:** alto
**Prioridade:** alta para manter automacao assistida-first
**Evidencia agregada:** $commit_flow_count sinal(is) sobre commit, push, merge, branch ou PR.
**Proposta:** registrar decisoes de merge no activity log, mas impedir que o learn-loop aplique mudancas procedurais automaticamente durante operacoes Git.
**Gates obrigatorios:** branch limpa, validacao completa, respeito a autorizacao explicita para merges/delecao de branches.
**Status recomendado:** proposto

EOF
  fi

  cat <<EOF
## Politica de Aplicacao

- Este arquivo contem candidatos, nao decisoes.
- Mudancas em skills, comandos, hooks e agentes exigem revisao humana.
- Fatos duraveis podem virar notas no vault; comportamento procedural deve virar PR/commit revisavel.
- Conteudo bruto de prompts permanece efemero e nao deve ser copiado para o vault.

## Proxima Acao Recomendada

Revisar os candidatos acima. Quando um candidato for aceito, criar uma tarefa especifica para implementar o patch correspondente com validacao e paridade Claude/Codex.
EOF
} > "$OUTPUT"

if [ -f "$ACTIVITY_LOG" ]; then
  printf '\n## [%s] learn-loop | %s prompts, %s activity entries, candidatos atualizados\n' \
    "$TIMESTAMP" "$prompt_count" "$activity_count" >> "$ACTIVITY_LOG"
fi

echo "learn-loop: candidatos atualizados em $OUTPUT"
