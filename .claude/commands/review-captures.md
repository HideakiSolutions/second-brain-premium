---
description: Revisa e aprova eventos auto-capturados em _pipeline/inbox/. Promove ao destino canônico ou descarta.
allowed-tools: Bash(.claude/scripts/event-router.sh*), Bash(.claude/scripts/vault-writer.sh*), Read, Edit, Bash(rm:*)
---

# /review-captures

Revisa o batch de eventos auto-capturados (modo `assisted`) em `_pipeline/inbox/auto-captures-YYYY-MM-DD.md` e os promove ao destino canônico (work-log, decisions, gotchas) ou descarta.

## Argumentos

- (sem argumento): revisa o arquivo do dia (`auto-captures-$(date)`).
- `--date YYYY-MM-DD`: revisa um dia específico.
- `--all`: processa todos os arquivos pendentes em `_pipeline/inbox/`.

## Passos

### 1. Processar fila de eventos pendentes

Antes de revisar, garantir que a fila está processada:

```bash
bash $VAULT/.claude/scripts/event-router.sh --once
```

### 2. Listar eventos no inbox

Ler `_pipeline/inbox/auto-captures-$(data).md`. Cada bloco tem:

```
## [TIMESTAMP] tipo | projeto (modo)
```json
{ payload completo }
```

### 3. Para cada evento, decidir

**Modos de decisão:**

- **promote**: chamar `vault-writer.sh` com os parâmetros corretos do evento.
  - Para `commit`: `vault-writer.sh append-work-log --project X --type feat/fix/chore --description "msg"`
  - Para `pr-merged`: idem com `--status merged`
  - Para `deploy`: `vault-writer.sh append-activity --op auto-deploy --project X --description "..."`
  - Para `degraded`: `vault-writer.sh append-gotcha --project X --severity high --description "..."`

- **discard**: descartar o bloco do inbox sem promover.

- **skip**: deixar para depois.

### 4. Atualizar inbox

- Para eventos promovidos: marcar com `[promoted]` no header e mover para a seção `## Promovidos`
- Para descartados: mover para seção `## Descartados`
- Para skips: deixar como está

### 5. Quando não há mais pendentes

- Se o arquivo `auto-captures-YYYY-MM-DD.md` ficou só com promovidos/descartados, mover para `_sessions/auto-captures-archive-YYYY-MM-DD.md`
- Apagar do inbox

### 6. Registrar no activity-log

```
## [YYYY-MM-DD HH:MM] review-captures | — N eventos processados (P promovidos, D descartados)
```

## Heurísticas para classificação automática

Se o usuário pedir `--auto-promote`, aplicar regras:

- Commit `feat`/`fix` em main/master → promote
- Commit `chore`/`docs` → discard se descrição < 60 chars; senão skip
- PR-merged com label `decision` → promote como decision
- Deploy em prod → promote
- Deploy em dev/hmg → discard

## Quando usar

- Diariamente, ao final do dia (mesmo timing de `/end-session`)
- Sempre que o `on-prompt-submit.sh` alertar "X auto-captures pending"
- Antes de `/weekly-review` para limpar inbox
