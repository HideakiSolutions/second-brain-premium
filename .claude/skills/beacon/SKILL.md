---
name: beacon
tier: full
version: "1.1"
description: "Farol que cruza vault (second-brain) + projeto (CWD) e aponta a próxima ação consolidando backlog canônico, _pipeline/, branches, PRs, work-log e gotchas. Auto-detecta projeto com GATE bloqueante, ordena por urgência, destaca desalinhamentos vault↔repo, recomenda UMA ação. NUNCA cruza atividades de outros projetos."
trigger: "usuário pergunta 'próximas atividades', 'o que fazer agora', 'qual a próxima coisa', 'agenda do projeto', 'roadmap', 'next up', 'what next', 'status do projeto', 'backlog ativo'; usuário inicia sessão num projeto registrado no vault sem foco definido; usuário acabou de mergear PR/feature e pergunta o que vem depois"
skip: "usuário está debugando arquivo/erro específico; tarefa explícita em curso (refactor/fix/feature) sem pedido de replanejamento; próxima ação já é óbvia do contexto da conversa atual; usuário pediu visão portfólio puro (use /pipeline); usuário pediu state focado de um único projeto sem cruzar com repo (use /focus)"
license: Apache-2.0
metadata:
  owner: sb-solutions
  inspired-by: second-brain/pipeline, second-brain/focus
  canonical_source: "second-brain/.claude/skills/beacon/SKILL.md (origem versionada). Cópia instalada em ~/.claude/skills/beacon/SKILL.md."
---

# Beacon — Full Protocol

> Tier 2: protocolo completo para cruzar vault + projeto e responder "qual a próxima atividade".
> **Origem versionada:** `second-brain/.claude/skills/beacon/SKILL.md`. A cópia em `~/.claude/skills/beacon/`
> é instalada e deve ser mantida em paridade com esta.

---

## INVARIANTE DE ESCOPO (project-scope discipline) — leia primeiro

O beacon é **estritamente project-scoped**. O bug histórico (2026-05-30) foi cruzar atividades de
**outros** projetos porque (a) o projeto não era validado antes da leitura e (b) o protocolo lia
`_memory/current-state.md` — que é um **rollup de PORTFÓLIO cross-project** (`# Current State — Portfolio
Rollup`) — como se fosse estado do projeto atual, e (c) filtrava `_pipeline/` por menção textual frouxa.

Regras invioláveis:

1. **GATE bloqueante (Step 0):** resolver o projeto ANTES de ler qualquer fonte. Se o projeto não for
   resolúvel/registrado, **PARAR** e degradar para `/pipeline` (portfólio explícito) — nunca "adivinhar"
   misturando fontes globais.
2. **PROIBIDO ler fontes de portfólio global quando há projeto ativo.** Especificamente: **não ler**
   `_memory/current-state.md`, `_memory/heartbeat-latest.md` global, nem `_knowledge/projects.md` inteiro.
   Use somente `_knowledge/projects/{p}/*`.
3. **`_pipeline/*.md` só entra por match DETERMINÍSTICO de `project:`** no frontmatter == projeto ativo.
   Entry sem campo `project:` é **ignorada** (e reportada como desalinhamento "pipeline sem project:"),
   nunca incluída por menção textual.
4. **Tudo que vier de hooks ambient cross-project** (ex.: `[VAULT] Pendencias detectadas`, auto-captures
   do inbox) é **awareness, não escopo** — não tratar como atividade do projeto atual.

---

## Tier vs comando vault

A partir de 2026-05-07 (ADR `2026-05-07-tasks-md-deterministic-flow`), há dois beacons:

- **`/beacon` (vault command, project-scoped)** — `_knowledge/projects/<projeto>/TASKS.md` é fonte única.
  Lê TASKS.md + git/PRs do projeto. Drift detector. Use quando o projeto tem TASKS.md.
- **Este SKILL.md (tier 2, full protocol)** — cruza vault + repo + git + gh. Use quando o projeto não tem
  TASKS.md ainda, ou para análise dentro de um projeto registrado sem TASKS.md.

Quando ambos disponíveis, prefira o comando vault (`/beacon <projeto>`) — barato, determinístico, já scoped.

---

## When to Use

**TRIGGER quando:**
- Usuário pergunta direção: "próximas atividades", "o que fazer agora", "agenda do projeto", "next up",
  "what next", "qual a próxima coisa", "roadmap", "status do projeto", "backlog ativo"
- Usuário inicia sessão num projeto registrado em `_knowledge/projects/` sem foco definido
- Usuário acabou de fechar uma entrega (PR mergeado, fase concluída) e pergunta o que vem depois

**SKIP quando:**
- Usuário está debugando arquivo/erro específico — não mude o foco
- Tarefa explícita em curso (refactor, fix, feature) sem pedido de replanejamento
- Próxima ação já é óbvia do contexto da conversa atual
- Usuário pediu visão portfólio puro → use `/pipeline`
- Usuário pediu state focado de um único projeto sem cruzar com repo → use `/focus <projeto>`

---

## Argumentos

`$ARGUMENTS` (opcional) = nome do projeto. Se informado, **tem prioridade** sobre a auto-detecção.

---

## Full Workflow

### Step 0 — GATE: resolver e validar projeto (BLOQUEANTE)

Resolver o projeto nesta ordem e **parar no primeiro que casar**:

```bash
VAULT=$VAULT
PROJECT="${ARGUMENTS:-}"

# 1) argumento explícito
if [ -n "$PROJECT" ]; then
  [ -d "$VAULT/_knowledge/projects/$PROJECT" ] || { echo "Projeto '$PROJECT' não registrado no vault."; echo "Disponíveis:"; ls "$VAULT/_knowledge/projects/"; exit 0; }
else
  # 2) CWD basename
  CAND=$(basename "$PWD")
  if [ -d "$VAULT/_knowledge/projects/$CAND" ]; then
    PROJECT="$CAND"
  # 3) CLAUDE.md do repo
  elif [ -f "$PWD/CLAUDE.md" ]; then
    PROJECT=$(grep -m1 -E "^Repository:|^# CLAUDE.md —" "$PWD/CLAUDE.md" | sed -E 's/.*[—:][[:space:]]*//; s/`//g')
    [ -d "$VAULT/_knowledge/projects/$PROJECT" ] || PROJECT=""
  fi
fi
```

**GATE — decisão obrigatória antes de QUALQUER leitura de conteúdo:**

- **Projeto resolvido E registrado no vault** → seguir para Step 1 com escopo travado em `$PROJECT`.
- **CWD tem sinais de projeto (`STATE.md`/`docs/canonical/`/`CLAUDE.md`) mas NÃO registrado no vault** →
  informar "projeto `<nome>` não registrado; sugiro `/end-session` para criar a estrutura" e operar só com
  as fontes do **repo** (sem tocar em `_pipeline/`, `current-state.md` ou outros projetos).
- **Nenhum projeto resolúvel (ex.: `cd /tmp`)** → **degradar explicitamente para `/pipeline`** (portfólio)
  e dizer isso ao usuário. **Não** seguir lendo fontes do vault como se fosse um projeto.

> O escopo `$PROJECT` resolvido aqui é o **único** escopo válido pelo resto do protocolo. Qualquer dado
> que não pertença a `$PROJECT` é descartado.

### Step 1 — Coletar dados em paralelo (somente do projeto resolvido)

**Hard cap: 30 arquivos lidos no total. Priorizar canonical sobre summaries.**

**Lado vault (`$VAULT/`) — APENAS do projeto `$PROJECT`:**

| Arquivo | Filtro |
|---|---|
| `_knowledge/projects/{p}/TASKS.md` | inteiro, se existir (fonte canônica preferida) |
| `_knowledge/projects/{p}/state.md` | inteiro (ou `{p}.md` como fallback) |
| `_knowledge/projects/{p}/roadmap.md` | fase atual + próximas |
| `_knowledge/projects/{p}/work-log.md` | últimas 3 entradas |
| `_knowledge/projects/{p}/gotchas.md` | inteiro |
| `_pipeline/*.md` | **SOMENTE** entries cujo frontmatter tenha `project: {p}` (match exato). Sem campo `project:` → ignorar. |

**PROIBIDO nesta etapa (fontes de portfólio global):**
- ❌ `_memory/current-state.md` — é rollup cross-project (`# Current State — Portfolio Rollup`).
- ❌ `_knowledge/projects.md` inteiro — índice de todos os projetos.
- ❌ `_pipeline/*.md` sem `project:` correspondente, ou que apenas "mencionem" o projeto no corpo.
- ❌ qualquer `_knowledge/projects/<outro>/*`.

**Lado projeto (CWD) — só se a CWD for o repo do projeto resolvido:**

| Arquivo | Limite |
|---|---|
| `STATE.md` (raiz) | inteiro |
| `docs/canonical/*/07-execution-backlog.md` | 200 linhas |
| `docs/canonical/*/06-current-vs-target.md` | 200 linhas |
| `.enterprise/.specs/decisions/ADR-*.md` | 10 mais recentes (mtime), só frontmatter |
| `.hseos/runs/**/STATUS.md` ou `.logs/summaries/*.md` | 1-3 mais recentes (mtime) |

**Comandos shell (não conta para cap de arquivos):**
- `git -C "$PWD" status --short`, `git branch --show-current`, `git branch -a`, `git log --oneline -10`
- `gh pr list --state open --limit 20 --json number,title,author,headRefName` (best-effort)

### Step 2 — Cruzar e extrair items

Para cada item (somente de fontes do projeto `$PROJECT`): ID/título, fonte, status
(BLOQUEADO/EM ANDAMENTO/REVIEW/BACKLOG/CONCLUÍDO recente), última atualização, próximo passo concreto, tipo.

### Step 3 — Classificar por urgência

1. **BLOQUEADO** → 2. **URGENTE** (sem update >7d ou prioridade alta) → 3. **EM ANDAMENTO** (branch/PR/fase)
→ 4. **REVIEW** → 5. **BACKLOG**.

### Step 4 — Detectar desalinhamentos vault ↔ projeto

- Item canônico do repo (`07-execution-backlog`/TASKS.md) sem reflexo em `_pipeline/` com `project:` do projeto.
- Entry de `_pipeline/` **sem campo `project:`** (defeito de dados — reportar para backfill).
- Branch ativa >14d sem PR e sem entry no `work-log.md`.
- ADR aprovada <30d sem mention em `decisions.md`.

### Step 5 — Montar output (PT-BR)

```markdown
# Beacon — {projeto} — {data}

## Escopo
Projeto: {projeto} | Fonte do escopo: {argumento|CWD|CLAUDE.md} | TASKS.md: {sim/não}

## Bloqueadores ativos
- [origem] descrição → ação proposta   {se vazio: "Nenhum."}

## Em andamento
- Branch atual: {branch} ({N} arquivos não commitados)
- Branches feature ativas / PRs abertos / Fases canônicas em curso

## Próximas (priorizadas)
| # | Item | Fonte | Tipo | Próximo passo |

## Stale (14+ dias)   {omitir se vazio}

## Desalinhamentos vault ↔ projeto
- {...}   {se vazio: "Vault e projeto alinhados."}

## Recomendação única
{Uma ação concreta para AGORA + justificativa de 1 linha — MANDATÓRIO}
```

---

## Rules

- **Project-scope é inviolável.** Nunca incluir item/atividade de projeto ≠ `$PROJECT`. Se em dúvida sobre
  a qual projeto um item pertence, **omitir** e listar em desalinhamentos.
- **GATE primeiro.** Nenhuma leitura de conteúdo antes de resolver `$PROJECT` no Step 0.
- **Sem fontes de portfólio global** quando há projeto ativo (ver lista PROIBIDO).
- **Output sempre em PT-BR**, direto. **Recomendação única mandatória.**
- **Não inventar items** — só relatar o que está nos arquivos lidos do projeto.
- **Degradação graceful:** sem projeto → `/pipeline` explícito; projeto não registrado → sugere `/end-session`;
  `gh` ausente → "PRs: gh CLI indisponível"; arquivo opcional ausente → omite a seção.
- **Read-only.** Não cria, não atualiza, não commita.

---

## Verification

1. `cd <projeto-registrado> && /beacon` → output lista SÓ items do projeto; seção "Escopo" mostra o projeto
   e a fonte do escopo. Nenhum item de outro projeto aparece.
2. `cd /tmp && /beacon` → degrada explicitamente para `/pipeline` (não lê projeto algum).
3. `/beacon <projeto-inexistente>` → lista projetos disponíveis e para (não lê fontes globais).
4. Conferir que `_memory/current-state.md` **não** é lido quando há projeto ativo (regressão do bug 2026-05-30).
5. Entry de `_pipeline/` sem `project:` → aparece em "Desalinhamentos", nunca em "Próximas".
