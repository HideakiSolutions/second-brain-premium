---
description: Busca semântica sobre todo o vault (Qdrant + bge-m3 local). Retorna top-K chunks com referências.
allowed-tools: Bash(.claude/scripts/sb-search.sh:*)
---

# /sb-search

Busca semântica em todo o vault second-brain.

## Argumentos

`$ARGUMENTS` é a query em linguagem natural.

Flags suportadas (passe como parte de $ARGUMENTS):

- `--k 5` — top-K resultados (default 10)
- `--kind decisions` — filtra por tipo (`patterns`, `features`, `decisions`, `learnings`, `projects`, `content`, etc.)
- `--project meu-projeto` — filtra por projeto
- `--json` — saída JSON crua

## Execução

Rodar:
```bash
bash .claude/scripts/sb-search.sh "<query do usuário>" [flags]
```

Não inventar resultados. O script consulta Qdrant local e retorna chunks com:
- arquivo fonte (path relativo)
- heading_path (breadcrumb)
- kind/project
- score (similaridade cosseno)
- snippet (200 primeiros chars)

## Quando usar

- "Já existe decisão sobre X?" → `/sb-search "decisão sobre X" --kind decisions --k 5`
- "Quais learnings sobre auth/JWT?" → `/sb-search "auth JWT" --kind learnings`
- "Que padrão é mais aplicável para minha tarefa?" → `/sb-search "<descrição da tarefa>" --kind patterns`
- "Trabalhei nisso em algum projeto?" → `/sb-search "<contexto>" --kind projects`

## Pré-requisito

Containers `sb-qdrant` e `sb-ollama` rodando. Verificar com:
```bash
bash .claude/scripts/sb-reindex.sh status
```

Se faltar bootstrap inicial, rodar:
```bash
bash .claude/scripts/sb-reindex.sh
```

## Output esperado

Tabela markdown com top-K chunks. Após retorno, oferecer:
- Ler o arquivo completo (Read tool)
- Refinar busca (com --kind ou --project)
- Cruzar com outros tipos
