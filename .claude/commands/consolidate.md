---
description: Ciclo de consolidação da memória ("sono") — compacta current-state, expira capturas, propõe merges de quase-duplicatas, promove sinapses aprendidas a sugestões de link e sincroniza o grafo com pesos no FalkorDB.
allowed-tools: Bash(.claude/scripts/sb-synapse.sh:*), Read
---

# /consolidate

Roda o ciclo de consolidação da memória do second brain. Nada é apagado: conteúdo compactado vai para histórico; propostas exigem curadoria humana.

## Fases

1. **compact** — `_memory/current-state.md` mantém os N rollups mais recentes; excedente vai íntegro para `_memory/current-state-history/`
2. **expire** — capturas pendentes vencidas movem para lane `expired` (memory-reviewer)
3. **dedup** — quase-duplicatas semânticas em `_decisions/`/`_learnings/` (proposta, gate humano)
4. **propose** — sinapses LEARNED fortes (nascidas de co-ativação repetida) viram sugestões de WikiLink real
5. **sync** — reconciliação da projeção FalkorDB (graph `synapse`, consultável via Cypher/MCP)
6. **report** — `_memory/synapse-report.md`

## Execução

```bash
bash .claude/scripts/sb-synapse.sh build          # garante grafo fresco
bash .claude/scripts/sb-synapse.sh reinforce      # reforça co-ativações da janela recente
bash .claude/scripts/sb-synapse.sh decay          # decaimento + poda de sinapses aprendidas fracas
bash .claude/scripts/sb-synapse.sh consolidate [--keep 10] [--no-dedup] [--no-falkor]
```

Depois, ler `_memory/synapse-report.md` e apresentar ao usuário:
- o resumo do ciclo (tamanhos antes/depois, contagens)
- as propostas de merge e de novos WikiLinks (decisão humana; NUNCA aplicar automaticamente)

## Quando usar

- Semanalmente (o cron `weekly-synapse-consolidate` roda automaticamente às segundas)
- Quando `_memory/current-state.md` passar de ~50KB
- Após período intenso de trabalho multi-projeto (muitas capturas/ativações acumuladas)

## Guardrails

- Propostas de merge e de link exigem aprovação humana antes de qualquer edição
- `--keep` mínimo razoável é 5; não compactar abaixo disso sem pedido explícito
- Se a stack semântica estiver offline, o ciclo roda sem a fase dedup (fail-soft)
