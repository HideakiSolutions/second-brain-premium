Você é o farol operacional do second-brain. Cruze o vault do projeto atual com o repositório na CWD e responda qual é a próxima ação concreta, sem escrever no vault.

## Descrição

Use quando o usuário perguntar próximas atividades, estado do projeto, roadmap ativo, "o que fazer agora", "next up" ou quando uma entrega acabou de ser fechada e é preciso escolher a próxima ação.

`/beacon` é read-only e estritamente project-scoped. Ele nunca mistura atividades de outros projetos.

## Argumentos

`$ARGUMENTS` pode conter o nome do projeto. Se vazio, detectar pelo basename da CWD ou por sinais locais do repositório.

## Passos

### 0. Resolver projeto antes de ler conteúdo

Resolver o projeto nesta ordem:

1. Projeto explícito em `$ARGUMENTS`.
2. Basename da CWD, se existir em `$VAULT/_knowledge/projects/{projeto}`.
3. Metadado local do repositório, se houver `CLAUDE.md`, `AGENTS.md` ou `STATE.md`.

Se o projeto não for resolvido:

- Degradar explicitamente para `/pipeline`.
- Não ler `_memory/current-state.md`, `_knowledge/projects.md` inteiro, `_pipeline/` inteiro nem pastas de outros projetos.

Se o projeto foi resolvido mas não está registrado no vault:

- Informar que o projeto não está registrado.
- Sugerir `/end-session {projeto}` para criar a estrutura.
- Operar apenas com fontes do repositório atual, sem consultar portfolio global.

### 1. Ler somente fontes do projeto resolvido

No vault, ler no máximo 30 arquivos, priorizando:

- `_knowledge/projects/{projeto}/TASKS.md`, se existir.
- `_knowledge/projects/{projeto}/state.md`.
- `_knowledge/projects/{projeto}/roadmap.md`.
- `_knowledge/projects/{projeto}/work-log.md` nas últimas entradas.
- `_knowledge/projects/{projeto}/gotchas.md`.
- `_pipeline/*.md` apenas quando o frontmatter tiver `project: {projeto}` com match exato.

No repositório atual, se a CWD corresponder ao projeto:

- `STATE.md`.
- `docs/canonical/*/07-execution-backlog.md`.
- `docs/canonical/*/06-current-vs-target.md`.
- ADRs recentes em `.specs/decisions/` ou `.enterprise/.specs/decisions/`.
- `git status --short`, branch atual, branches recentes e `git log --oneline -10`.
- `gh pr list --state open --limit 20 --json number,title,author,headRefName`, best effort.

### 2. Priorizar

Classificar itens somente do projeto resolvido:

1. Bloqueado.
2. Urgente ou stale.
3. Em andamento.
4. Review.
5. Backlog.

Detectar desalinhamentos:

- Item canônico no repo sem reflexo em `_pipeline/` com `project:`.
- Entry de `_pipeline/` sem `project:`.
- Branch ativa antiga sem PR e sem work-log.
- ADR recente sem reflexo em `decisions.md`.

## Saída

Responder em PT-BR:

```markdown
# Beacon — {projeto} — {data}

## Escopo
Projeto: {projeto} | Fonte do escopo: {argumento|CWD|metadado local} | TASKS.md: {sim|nao}

## Bloqueadores ativos
- ...

## Em andamento
- Branch atual: ...
- PRs / fases / tarefas ativas: ...

## Próximas priorizadas
| # | Item | Fonte | Tipo | Próximo passo |
|---|---|---|---|---|

## Desalinhamentos vault x projeto
- ...

## Recomendação única
{uma ação concreta para agora + justificativa de 1 linha}

**vault:** nao aplicavel
```

## Regras

- Read-only: não criar, editar, commitar, reindexar nem densificar.
- Escopo de projeto é inviolável; se um item não pertence claramente ao projeto resolvido, omitir.
- Resolver o projeto antes de qualquer leitura de conteúdo.
- Não ler fontes globais de portfolio quando há projeto ativo.
- `_pipeline/` só entra por `project:` no frontmatter com match exato.
- Sem projeto resolvido, usar `/pipeline` como fallback explícito.
- A saída final sempre deve conter `vault: nao aplicavel`.
