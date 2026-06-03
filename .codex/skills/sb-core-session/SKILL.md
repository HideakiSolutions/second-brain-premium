---
name: sb-core-session
description: "Você é o analisador de core do segundo cérebro. Cruze o conhecimento do vault com os repositórios base do portfólio."
license: Apache-2.0
metadata:
  owner: second-brain
  vault: "$VAULT"
  vault_name: "Second Brain"
  vault_prefix: "sb"
  source_command: ".claude/commands/core-session.md"
---

# Second Brain Core Session

This is the Codex port of `core-session` from `.claude/commands/core-session.md`.

When the original command mentions `$ARGUMENTS`, treat it as the current user input or the text following the skill invocation.

Use `$VAULT` as the vault root for all relative paths unless the user provides another path.

# Core Session — Módulo Opcional: Core Registry

> **Este comando é para quem usa o padrão de Core Registry.**
> Se você não tem cores (bibliotecas/serviços base compartilhados entre projetos), este comando não se aplica.
> Para ativar: configure `_cores/` com seus repos base conforme documentado no CLAUDE.md.

Você é o analisador de core do segundo cérebro. Cruze o conhecimento do vault com os repositórios base do portfólio.

## O que é Core Registry?

Um "core" é um repositório ou módulo base compartilhado por múltiplos projetos. Exemplos:
- `platform-core` — auth, logging, observabilidade
- `backend-core` — estrutura hexagonal, CQRS, persistence abstractions
- `frontend-core` — componentes, design tokens, state management
- `mobile-core` — navegação, auth, componentes nativos

O `_cores/promotion-backlog.md` rastreia features de projetos que deveriam ser promovidas para um core.

## Argumentos

`$ARGUMENTS` pode ser:
- `new [nome-do-projeto]` — gera checklist de derivação para novo projeto
- `[nome-de-projeto]` — análise de drift focada num projeto existente
- vazio — análise completa + relatório de candidatos a promoção

---

## Passos

### 1. Carregar contexto de cores

Ler (sempre):
- `_cores/README.md` — o que cada core oferece
- `_cores/promotion-backlog.md` — candidatos a promoção

Se existir `_index/FEATURE-CATALOG.md`, ler para cruzar features com cores.

Ler adicionalmente conforme modo:
- Se projeto frontend → `_cores/frontend-core.md` (se existir)
- Se projeto específico → `_knowledge/projects/{projeto}/{projeto}.md`

---

### 2. Modo `new [nome]` — Checklist de Derivação

Gerar checklist do que o novo projeto deve derivar de cada core:

```markdown
## Checklist de Derivação — {nome}

### De cada core (listar o que é oferecido e marcar o que o projeto precisa)
- [ ] {módulo/feature do core} — origem: {core}

### O que NÃO reimplementar
{Features já disponíveis nos cores que o projeto deve consumir}

### O que está em aberto (gaps nos cores)
{O que o projeto vai precisar mas não existe nos cores ainda}
```

---

### 3. Modo `[projeto]` — Análise de Drift

**3a. Mapear consumo atual**
Cruzar o projeto com os cores disponíveis.

**3b. Identificar drift**
- O projeto implementou algo que já está em algum core?
- O projeto usa versão desatualizada de um padrão?

**3c. Identificar candidatos a promoção**
- Features usadas em 2+ projetos → candidato a core
- Features que resolvem gaps documentados → alta prioridade

**3d. Relatório:**
```
## Drift Analysis — {projeto}
### Consumo correto
### Drift detectado
### Candidatos a promoção
### Ações recomendadas
```

---

### 4. Modo vazio — Análise Completa

Para todos os projetos ativos:
- Executar análise de drift simplificada
- Agregar candidatos a promoção (deduplicar)
- Agregar gaps de core detectados

---

### 5. Atualizar `_cores/promotion-backlog.md`

Para cada candidato novo identificado:
```
| {YYYY-MM-DD} | {feature} | {projeto-origem} | {N projetos} | {core-alvo} | {critério} | candidato |
```

### 6. Registrar no activity log

Append em `_memory/activity-log.md`:
```
## [YYYY-MM-DD HH:MM] update | core-session: {modo} — {N candidatos}, {N gaps}
```

---

## Output

Responda **em português (BR)** com os resultados da análise.

## Regras

- Nunca propor promoção sem evidência de reuso (2+ projetos ou gap documentado)
- Promoção requer ADR — apenas sugerir, não executar
- Drift não é erro — é informação. Documentar sem julgamento
