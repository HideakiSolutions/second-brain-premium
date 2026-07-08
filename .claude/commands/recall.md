---
description: Recall associativo sobre o vault — sementes semânticas + propagação pelas sinapses + força de uso. Cada resultado explica a cadeia de memórias que o trouxe.
allowed-tools: Bash(.claude/scripts/sb-synapse.sh:*)
---

# /recall

Recall associativo no second brain: uma memória puxa a outra. Combina similaridade semântica (Qdrant), propagação de ativação pelo grafo sináptico (links tipados com peso) e força de memória (frequência × recência de uso).

## Argumentos

`$ARGUMENTS` é a query em linguagem natural OU `--seed <slug>` para expandir associativamente a partir de uma nota específica.

Flags suportadas (passe como parte de $ARGUMENTS):

- `--k 8` — top-K memórias (default 8)
- `--hops 2` — profundidade da propagação sináptica (default 2)
- `--kind decisions` — filtra por tipo (`patterns`, `features`, `decisions`, `learnings`, `projects`, etc.)
- `--project <slug>` — filtra por projeto
- `--seed <slug>` — modo associativo puro: parte de uma nota e segue as sinapses (não requer query; funciona offline)
- `--json` — saída JSON crua
- `--brief` — uma linha por resultado

## Execução

```bash
bash .claude/scripts/sb-synapse.sh recall "<query do usuário>" [flags]
```

Não inventar resultados. Cada memória retorna com:
- score composto (semântico + ativação propagada + força)
- a CADEIA que levou até ela (`seed → intermediária → memória`)
- sugestões de próximos saltos (vizinhas fortes fora do top-K)

O recall registra ativações (sinal hebbiano): o que você recupera junto se conecta mais forte. Use `--no-log` apenas para consultas exploratórias que não devem reforçar sinapses.

## Quando usar

- "O que o vault sabe sobre X, incluindo o contexto vizinho?" → `/recall "X"`
- "O que essa decisão/nota puxa?" → `/recall --seed <slug-da-nota>`
- "Como duas memórias se conectam?" → `bash .claude/scripts/sb-synapse.sh explain <slug-a> <slug-b>`
- Precedente antes de decidir → `/recall "<proposta>" --kind decisions`

Prefira `/recall` a `/search` quando o contexto AO REDOR dos hits importa (decisão ligada ao gotcha ligado ao projeto). Use `/search` para lookup pontual de chunks.

## Pré-requisito

- Grafo sináptico construído: `bash .claude/scripts/sb-synapse.sh build` (rápido, idempotente)
- Para query semântica: stack local ativa (`bash _bootstrap/agentic/stack.sh status`)
- Modo `--seed` funciona 100% offline (não usa Qdrant/Ollama)

Se a stack estiver offline, o comando retorna erro acionável — não anunciar fallback grep.

## Output esperado

Lista rankeada com score decomposto, cadeia de cada memória e próximos saltos. Após retorno, oferecer:
- Ler a memória completa (Read tool)
- Expandir um resultado (`--seed <slug>`)
- Explicar uma conexão (`explain`)
