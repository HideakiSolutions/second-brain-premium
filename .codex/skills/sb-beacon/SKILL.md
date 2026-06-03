---
name: sb-beacon
description: "Farol read-only project-scoped que cruza vault e repositorio atual para recomendar a proxima acao concreta."
license: Apache-2.0
metadata:
  owner: second-brain
  vault: "$VAULT"
  vault_name: "Second Brain"
  vault_prefix: "sb"
  source_command: ".claude/commands/beacon.md"
---

# Second Brain Beacon

This is the Codex port of `beacon` from `.claude/commands/beacon.md`.

Use quando o usuario perguntar proximas atividades, estado do projeto, roadmap ativo, "o que fazer agora", "next up" ou quando uma entrega acabou de ser fechada e e preciso escolher a proxima acao.

## Workflow

1. Resolva o projeto antes de ler conteudo:
   - use argumento explicito quando houver;
   - senao use basename da CWD se existir em `$VAULT/_knowledge/projects/{projeto}`;
   - senao use sinais locais como `AGENTS.md`, `CLAUDE.md` ou `STATE.md`.
2. Se nenhum projeto for resolvido, degrade explicitamente para `sb-pipeline` e nao leia fontes globais como se fossem projeto.
3. Se o projeto foi resolvido mas nao esta registrado no vault, informe isso, sugira `sb-end-session {projeto}` e opere apenas com fontes do repositorio atual.
4. Leia somente fontes do projeto resolvido:
   - `_knowledge/projects/{projeto}/TASKS.md`, se existir;
   - `_knowledge/projects/{projeto}/state.md`;
   - `_knowledge/projects/{projeto}/roadmap.md`;
   - ultimas entradas de `_knowledge/projects/{projeto}/work-log.md`;
   - `_knowledge/projects/{projeto}/gotchas.md`;
   - `_pipeline/*.md` apenas com `project: {projeto}` no frontmatter.
5. Se a CWD corresponder ao projeto, leia fontes locais proporcionais:
   - `STATE.md`;
   - `docs/canonical/*/07-execution-backlog.md`;
   - `docs/canonical/*/06-current-vs-target.md`;
   - ADRs recentes em `.specs/decisions/` ou `.enterprise/.specs/decisions/`;
   - `git status --short`, branch atual, branches recentes e `git log --oneline -10`;
   - `gh pr list --state open --limit 20 --json number,title,author,headRefName`, best effort.
6. Classifique itens por bloqueado, urgente/stale, em andamento, review e backlog.
7. Detecte desalinhamentos vault x projeto.
8. Responda em PT-BR com escopo, bloqueadores, em andamento, proximas priorizadas, desalinhamentos e uma recomendacao unica.

## Output obrigatório

Encerrar com:

```markdown
**vault:** nao aplicavel
```

## Regras

- Read-only: nao criar, editar, commitar, reindexar nem densificar.
- Escopo de projeto e inviolavel; se um item nao pertence claramente ao projeto resolvido, omitir.
- Resolver o projeto antes de qualquer leitura de conteudo.
- Nao ler fontes globais de portfolio quando ha projeto ativo.
- `_pipeline/` so entra por `project:` no frontmatter com match exato.
- Sem projeto resolvido, usar `sb-pipeline` como fallback explicito.
- A resposta final sempre deve conter `vault: nao aplicavel`.
