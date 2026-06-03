---
name: sb-session-handoff
description: "Você é o gerador de handoff do segundo cérebro. Crie um artefato estruturado para que a próxima sessão retome o trabalho sem perda de contexto."
license: Apache-2.0
metadata:
  owner: second-brain
  vault: "$VAULT"
  vault_name: "Second Brain"
  vault_prefix: "sb"
  source_command: ".claude/commands/session-handoff.md"
---

# Second Brain Session Handoff

This is the Codex port of `session-handoff` from `.claude/commands/session-handoff.md`.

When the original command mentions `$ARGUMENTS`, treat it as the current user input or the text following the skill invocation.

Use `$VAULT` as the vault root for all relative paths unless the user provides another path.

Você é o gerador de handoff do segundo cérebro. Crie um artefato estruturado para que a próxima sessão retome o trabalho sem perda de contexto.

---

## Contexto

Sessões de desenvolvimento terminam frequentemente no meio de uma tarefa. Sem handoff estruturado, a próxima sessão precisa re-descobrir contexto, reler os mesmos arquivos e, muitas vezes, repetir tentativas que já falharam.

Esta skill cria um `HANDOFF.md` que habilita retomada imediata com contexto completo.

**Relação com o segundo cérebro:** O `/end-session` captura conhecimento de nível de vault (ADRs, gotchas, aprendizados). O `HANDOFF.md` captura estado de nível de sessão (trabalho em andamento, o que fazer a seguir). Eles se complementam - use ambos.

---

## Quando usar

- Antes de encerrar qualquer sessão que deixou tarefa incompleta
- Antes de compactação de contexto em tarefa longa
- Sempre que a próxima ação requer contexto que não está no codebase

---

## Passos

### 1. Verificar HANDOFF.md existente

```bash
ls HANDOFF.md 2>/dev/null && cat HANDOFF.md || echo "Sem handoff existente"
```

Se existir, ler. Fazer append - nunca sobrescrever sem ler primeiro.

### 2. Coletar estado da sessão

```bash
git diff --name-only        # arquivos alterados
git branch --show-current   # branch atual
git status                  # trabalho não commitado
git log -1 --oneline        # último commit
```

### 3. Criar HANDOFF.md

```markdown
# HANDOFF — <nome da feature ou tarefa>
**Data:** YYYY-MM-DD HH:MM
**Branch:** <nome do branch>
**Tipo:** feature | fix | task | spike

## Objetivo
<uma frase - o resultado específico que esta sessão estava perseguindo>

## Progresso atual

### Concluído
- [x] <item> — `<caminho do arquivo se relevante>`
- [x] <item>

### Em andamento (continuar aqui)
- [ ] <item> — `<arquivo>` — <próxima ação específica>

### Não iniciado
- [ ] <item>

## O que funcionou
- **<abordagem>:** <por que funcionou, o que replicar>

## O que NÃO funcionou (não tentar de novo)
- **<abordagem>:** <por que falhou, o que evitar>

## Decisões tomadas nesta sessão
- <decisão> — racional: <por quê>
- Se gerou ADR: ver `_decisions/<YYYY-MM-DD>-<desc>.md`

## Perguntas abertas / Bloqueios
- [ ] <pergunta que precisa de decisão humana>
- [ ] <bloqueio aguardando dependência externa>

## Próximos passos (em ordem)
1. `<arquivo exato>` — <ação exata>
2. `<arquivo exato>` — <ação exata>
3. Executar: `<comando exato>`

## Contexto não óbvio pelo código
- <gotcha, suposição ou restrição não óbvia que a próxima sessão precisa saber>
```

### 4. Gitignore

```bash
grep -q "HANDOFF.md" .gitignore || echo "HANDOFF.md" >> .gitignore
```

HANDOFF.md é estado de sessão, não artefato permanente - não deve ser commitado.

### 4b. SESSION-CHECKPOINT (para sessões que serão retomadas na mesma tarefa)

Se a próxima sessão vai retomar exatamente esta tarefa, criar também `SESSION-CHECKPOINT.md`:

```markdown
# SESSION-CHECKPOINT — <nome da feature ou tarefa>
**Data:** YYYY-MM-DD HH:MM
**Branch:** <branch>
**Status no checkpoint:** <resumo de uma linha de onde paramos>

## Decisões desta sessão
- <decisão 1> — racional: <por quê>
- <decisão 2> — racional: <por quê>

## Em aberto (ainda não feito)
- [ ] <item> — <arquivo> — <próxima ação exata>

## Pular (já feito, não refazer)
- <item> — concluído em: <arquivo ou commit>

## Prompt de retomada
> "<colar este prompt verbatim para retomar na velocidade máxima>"
```

```bash
grep -q "SESSION-CHECKPOINT.md" .gitignore || echo "SESSION-CHECKPOINT.md" >> .gitignore
```

### 5. Sincronizar com o vault (se a sessão foi produtiva)

Conforme `CLAUDE.md §3`, também registrar no vault:
- Decisões arquiteturais → `_knowledge/projects/{projeto}/decisions.md`
- Gotchas descobertos → `_knowledge/projects/{projeto}/gotchas.md`
- Activity log → `_memory/activity-log.md`
- Estado geral → `_memory/current-state.md`

---

## Anti-padrões

| Anti-padrão | Por que falha |
|-------------|--------------|
| "O contexto vai estar no código" | Código não explica por que tentativas falharam |
| "Vou lembrar onde parei" | Nova sessão = zero memória |
| Entradas vagas ("trabalhei em auth") | Inútil - próxima sessão ainda precisa re-descobrir |
| Não registrar tentativas que falharam | Próxima sessão vai repetir os mesmos erros |
| Commitar HANDOFF.md | Polui histórico git com estado efêmero |

---

## Critérios de saída (Definition of Done)

- [ ] HANDOFF.md criado com todas as seções preenchidas
- [ ] "Em andamento" tem arquivo específico e próxima ação exata
- [ ] "O que NÃO funcionou" registra todas as abordagens tentadas que falharam
- [ ] HANDOFF.md está no `.gitignore`
- [ ] SESSION-CHECKPOINT.md criado se a sessão vai ser retomada na mesma tarefa
- [ ] Vault atualizado via `/end-session` para decisões ou gotchas descobertos

---

## Regras

- Handoff deve ser criado antes de encerrar a sessão - depois significa que o contexto já foi perdido
- "Curta" não é critério para pular handoff - "incompleta" é
- Seção "O que NÃO funcionou" não pode ficar vazia em sessão que teve tentativas fracassadas
- Next Steps sem referência a arquivo específico ou comando exato é inútil
- Sempre verificar HANDOFF.md existente antes de criar um novo
