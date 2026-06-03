---
name: sb-densify
description: "Roda auto-linker, concept-extractor e pattern-matrix-generator em sequência. Mostra delta de densidade."
license: Apache-2.0
metadata:
  owner: second-brain
  vault: "$VAULT"
  vault_name: "Second Brain"
  vault_prefix: "sb"
  source_command: ".claude/commands/densify.md"
---

# Second Brain Densify

This is the Codex port of `densify` from `.claude/commands/densify.md`.

When the original command mentions `$ARGUMENTS`, treat it as the current user input or the text following the skill invocation.

Use `$VAULT` as the vault root for all relative paths unless the user provides another path.


# /densify

Densifica o knowledge graph executando os scripts determinísticos em sequência.

## Argumentos opcionais

- Sem argumento: dry-run em todo o vault, mostra o que seria mudado
- `--apply`: aplica as mudanças
- `--scope <path>`: limita a um diretório (ex: `_knowledge/projects/meu-projeto`)

## Execução

### Modo dry-run (default)

1. Rodar `bash .claude/scripts/graph-metrics.sh` — captura métricas baseline
2. Se houver broken links, tratar como bloqueio: corrigir links quebrados antes de adicionar novos
3. Rodar `bash .claude/scripts/auto-linker.sh` (sem `--apply`) — lista links que SERIAM criados
4. Mostrar resumo: quantos arquivos seriam tocados, quantos links novos
5. Pedir confirmação antes de aplicar

### Modo --apply

1. `bash .claude/scripts/graph-metrics.sh` — baseline
2. Confirmar que baseline tem `Broken links: 0`; se não tiver, abortar
3. `bash .claude/scripts/auto-linker.sh --apply` — aplica WikiLinks
4. `bash .claude/scripts/concept-extractor.sh` — regenera CONCEPT-INDEX
5. `bash .claude/scripts/pattern-matrix-generator.sh` — regenera matrices
6. `bash .claude/scripts/graph-metrics.sh` — métricas pós
7. Mostrar delta: ilhas (antes → depois), grau médio (antes → depois), backlinks novos

## Output esperado

```
[densify] Baseline: 42.9% ilhas, grau 3.23
[auto-linker] [APPLY] 96 arquivo(s), 312 link(s) novo(s)
[concept-extractor] 24 docs, 20 concepts → _index/CONCEPT-INDEX.md
[matrix-gen] PATTERN-MATRIX.md / FEATURE-CATALOG.md atualizados
[densify] Pós: 18.4% ilhas, grau 8.7
[densify] Δ: -24.5pp ilhas · +5.47 grau · +312 links
```

## Quando usar

- Após bootstrap inicial da Fase A
- Periodicamente após adicionar novos arquivos a `_knowledge/projects/`
- Antes de revisões semanais

## Regra

Densificação não é cura de grafo. Primeiro remover links quebrados e placeholders; depois adicionar links novos. Se `auto-linker` sugerir link para conceito genérico demais ou candidato ainda não canonizado, não aplicar automaticamente.
