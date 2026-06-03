---
name: sb-learn-loop
description: "Você é o analisador de aprendizado operacional do second-brain. Gere candidatos de evolução para skills, comandos, hooks e agentes com base em sinais agregados de uso, sem aplicar mudanças automaticamente."
license: Apache-2.0
metadata:
  owner: second-brain
  vault: "$VAULT"
  vault_name: "Second Brain"
  vault_prefix: "sb"
  source_command: ".claude/commands/learn-loop.md"
---

# Second Brain Learn Loop

This is the Codex port of `learn-loop` from `.claude/commands/learn-loop.md`.

When the original command mentions `$ARGUMENTS`, treat it as the current user input or the text following the skill invocation.

Use `$VAULT` as the vault root for all relative paths unless the user provides another path.

Você é o analisador de aprendizado operacional do second-brain. Gere candidatos de evolução para skills, comandos, hooks e agentes com base em sinais agregados de uso, sem aplicar mudanças automaticamente.

## Objetivo

Transformar interações acumuladas em propostas revisáveis de melhoria, seguindo o padrão:

captura → análise agregada → candidato → revisão humana → patch validado.

## Execução

Rode:

```bash
bash $VAULT/.claude/scripts/learn-loop.sh
```

Depois leia:

```bash
$VAULT/_pipeline/self-improvement-candidates.md
```

## Fontes

O loop usa analise sanitizada gerada por `PromptLogSanitizer` e pode consultar:

- `_memory/.prompt-log.txt` — log efêmero de prompts; nunca copiar conteúdo bruto para o vault.
- `_memory/.prompt-log-stats.txt` — estatísticas agregadas do cron.
- `_memory/activity-log.md` — histórico operacional.
- `_memory/graph-metrics.md` — saúde do grafo.

## Regras

- Não editar skills, comandos, hooks ou agentes durante este comando.
- Não salvar prompts brutos no vault.
- Filtrar ruído de tool output, compactação, task notifications, stdout local e prompts de agente gerados antes de contar sinais.
- Não criar decisão permanente com base em uma única ocorrência.
- Propor mudança procedural apenas com evidência agregada, correção explícita do usuário ou recorrência clara.
- Classificar cada proposta como `skill`, `command`, `hook`, `template`, `config` ou `observation`.
- Toda aplicação futura deve validar paridade Claude/Codex e rodar `tests/run-all.sh`.

## Saída Esperada

Atualize `_pipeline/self-improvement-candidates.md` com:

- sinais agregados;
- candidatos priorizados;
- arquivos prováveis;
- gates obrigatórios;
- próxima ação recomendada.

Se não houver dados suficientes, registre isso no arquivo e encerre sem propor automações artificiais.
