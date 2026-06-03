---
description: Re-indexa o vault no Qdrant via embeddings bge-m3. Idempotente. Use após mudanças significativas.
allowed-tools: Bash(.claude/scripts/sb-reindex.sh:*)
---

# /sb-reindex

Re-indexação do vault second-brain no Qdrant local.

## Argumentos

- (sem argumento): re-indexa o vault inteiro com `--replace` (idempotente — apaga pontos antigos primeiro).
- `--paths <p1> <p2> ...`: re-indexa apenas paths especificados.
- `status`: mostra estado da infra (Qdrant + Ollama + collection).

## Execução

```bash
bash .claude/scripts/sb-reindex.sh [args]
```

## Quando usar

- **Bootstrap inicial** (uma vez): `/sb-reindex`
- **Após bulk edit** (ex: pós-`/densify`): `/sb-reindex`
- **Após criar/editar uma nota crítica** (ADR, learning relevante): `/sb-reindex --paths _decisions/X.md`
- **Verificar saúde da infra**: `/sb-reindex status`

## Custos

- 100% local. Embeddings via Ollama bge-m3 na CPU.
- ~1-2 chunks/segundo. Vault de 2700 chunks → ~25-30 minutos para bootstrap completo.
- Re-indexação parcial é instantânea.

## Pré-requisito

Containers Docker iniciados:
```bash
cd _bootstrap/agentic && docker compose up -d
docker exec sb-ollama ollama pull bge-m3   # apenas primeira vez (~1.2GB)
```
