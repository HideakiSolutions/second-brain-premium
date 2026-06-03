---
name: sb-reindex
description: "Re-indexa o vault no Qdrant via embeddings bge-m3. Idempotente. Use após mudanças significativas."
license: Apache-2.0
metadata:
  owner: second-brain
  vault: "$VAULT"
  vault_name: "Second Brain"
  vault_prefix: "sb"
  source_command: ".claude/commands/reindex.md"
---

# Second Brain Sb Reindex

This is the Codex port of `sb-reindex` from `.claude/commands/sb-reindex.md`.

When the original command mentions `$ARGUMENTS`, treat it as the current user input or the text following the skill invocation.

Use `$VAULT` as the vault root for all relative paths unless the user provides another path.


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
