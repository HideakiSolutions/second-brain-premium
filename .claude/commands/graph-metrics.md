---
description: Gera relatório de saúde do grafo (ilhas, hubs, broken links, tags fora da taxonomia)
allowed-tools: Bash(.claude/scripts/graph-metrics.sh), Read(_memory/graph-metrics.md)
---

# /graph-metrics

Snapshot do estado do knowledge graph do vault.

## Execução

1. Rodar `bash .claude/scripts/graph-metrics.sh` (ou `python3 .claude/scripts/lib/graph_metrics.py`)
2. Ler `_memory/graph-metrics.md` recém gerado
3. Imprimir resumo para o usuário com:
   - Total de arquivos analisados
   - % de ilhas (zero links de saída)
   - Grau médio
   - Top 5 hubs
   - Quantidade de broken links e de tags fora da taxonomia
   - Cobertura projetos×patterns (quantos atingem ≥3 patterns linkados)

## Targets de qualidade (referência)

- Ilhas ≤ 15%
- Projetos com ≥3 patterns linkados: ≥ 90% (15/16)
- Patterns com ≥2 backlinks: 100%
- Grau médio ≥ 8
- Tags fora taxonomia: 0
- Broken links: 0

## Quando usar

- Antes de iniciar densificação (`/densify`) — captura baseline
- Após densificação — confirma evolução
- Em `/end-session` para registrar evolução do grafo
- Periodicamente para detectar regressões
