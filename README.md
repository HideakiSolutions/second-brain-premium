# second-brain-premium

> **Vault operacional para AI-SDLC com paridade Claude/Codex, busca semântica opcional (Qdrant + Ollama), memória associativa sináptica (recall com reforço por uso) e governança agêntica — derivado do [second-brain-starter](https://github.com/marciohideaki/second-brain-starter) com capacidades enterprise: 39 slash commands, 5 hooks, 3 crons, dev-squad multi-agente, pipeline editorial e biblioteca de padrões arquiteturais.**

[![Claude Code](https://img.shields.io/badge/Claude%20Code-ready-blue)](https://docs.anthropic.com/claude-code)
[![Codex CLI](https://img.shields.io/badge/Codex-paridade%201%3A1-green)](https://github.com/openai/codex)
[![Status: v0.1.0](https://img.shields.io/badge/release-v0.1.0-orange)]()

**Para quem é**: engenheiros de software, arquitetos, tech leads, founders e times que praticam AI-SDLC — quem precisa de memória persistente entre sessões, governança formal de decisões e múltiplos projetos em paralelo.

**O que torna diferente do starter**: enquanto o `second-brain-starter` é um kit minimalista de 12 skills para uso pessoal, este premium adiciona **paridade Codex completa**, **stack semântico local (Qdrant + Ollama)**, **dev-squad multi-agente**, **biblioteca de padrões e features arquiteturais**, **pipeline de entrega formal** (delivery-closeout, completion-audit, live-deploy-validate) e um **contrato agêntico durável** em AGENTS.md.

👉 **Primeira vez?** Vá direto para [Primeiros 30 minutos](#primeiros-30-minutos).

---

## Índice

- [O que é um second brain "Premium"](#o-que-é-um-second-brain-premium)
- [O que faz, em uma frase](#o-que-faz-em-uma-frase)
- [Pré-requisitos](#pré-requisitos)
- [Instalação](#instalação)
- [Primeiros 30 minutos](#primeiros-30-minutos)
- [Os 39 slash commands](#os-39-slash-commands)
- [Paridade Claude ↔ Codex](#paridade-claude--codex)
- [Stack semântico opcional (Qdrant + Ollama)](#stack-semântico-opcional-qdrant--ollama)
- [Governança e hooks](#governança-e-hooks)
- [Testes e lint](#testes-e-lint)
- [Como difere de outras opções](#como-difere-de-outras-opções)
- [Filosofia](#filosofia)
- [Estrutura do repositório](#estrutura-do-repositório)
- [FAQ](#faq)
- [Troubleshooting](#troubleshooting)
- [Licença](#licença)
- [🇬🇧 English summary](#-english-summary)

---

## O que é um second brain "Premium"

A versão "starter" (OSS) é um kit pessoal mínimo para quem quer começar. Este "premium" assume que você opera **múltiplos projetos enterprise**, com:

- Decisões arquiteturais que precisam de ADRs rastreáveis
- Padrões reutilizáveis entre projetos (CQRS, saga, outbox, idempotency, etc.)
- Pipeline de entrega com gates (audit → validate → deploy → closeout)
- Múltiplos agentes (Claude + Codex) que precisam compartilhar o mesmo contrato
- Necessidade de busca semântica sobre centenas de notas, não só dezenas

Tudo localmente, em markdown, sem cloud lock-in. O contrato agêntico vive em [`AGENTS.md`](AGENTS.md) — qualquer agente que opere neste repo deve lê-lo primeiro.

## O que faz, em uma frase

Você tem 39 comandos que cobrem o ciclo completo do AI-SDLC — desde captura de ideia até entrega validada — e tudo o que você produz fica em markdown organizado por convenções estritas, recuperável via busca semântica, e paritário entre Claude Code e Codex.

---

## Pré-requisitos

### Obrigatório

1. **bash** — Git Bash no Windows, terminal nativo em macOS/Linux/WSL.
2. **git** — para versionamento.
3. **Claude Code** ou **Codex CLI** — pelo menos um dos dois:
   - Claude Code: `npm install -g @anthropic-ai/claude-code` ([docs](https://docs.anthropic.com/claude-code))
   - Codex CLI: ver [github.com/openai/codex](https://github.com/openai/codex)

### Opcional (mas recomendado)

4. **Python 3.11+** — necessário para subsistemas `curator/`, `predictor/`, `style/profiler.py` e para o hook `secret-guard`.
5. **Docker** *ou* binários nativos — para o stack semântico (Qdrant + Ollama). O `stack.sh` suporta os dois modos; sem o stack, todos os comandos que dependem dele degradam para fallback determinístico (grep + Read).
6. **`gh` CLI** — se quiser usar comandos que tocam GitHub (PRs, issues).
7. **crontab** — Linux/macOS/WSL. Para os 4 crons opcionais (daily-heartbeat, weekly-vault-lint, weekly-core-session, weekly-synapse-consolidate).

### Plataformas

- **Linux / macOS**: suporte nativo total.
- **Windows**: roda via Git Bash. Crons via Task Scheduler (não inclusos automaticamente). Notificações via toast nativo do Windows (fallback bell se indisponível).
- **WSL2**: idêntico a Linux.

---

## Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/HideakiSolutions/second-brain-premium.git ~/second-brain-premium
cd ~/second-brain-premium

# 2. Rode o installer interativo (recomendado)
./install.sh
```

O installer é **agnóstico** (zero paths hardcoded) e **idempotente** (pode rodar várias vezes). Pergunta cada destino, faz backup de qualquer arquivo externo antes de modificar, e nunca usa `sudo`. Componentes que cobre:

| # | Componente | Descrição |
|---|---|---|
| 1 | Slash commands | Symlink/copy de `.claude/commands/*.md` → seu `~/.claude/commands/` |
| 2 | Skills Codex | Symlink/copy de `.codex/skills/sb-*/` → seu `~/.codex/skills/` |
| 3 | Hooks | Merge idempotente de `.claude/settings.json` com backup `.bak.<timestamp>` |
| 4 | CLAUDE.md global | Append (ou atualiza) bloco "Second Brain" no `~/.claude/CLAUDE.md` global |
| 5 | Crons | Mostra linhas para você colar manualmente (nunca modifica crontab) |
| 6 | Stack semântico | Pergunta o modo (docker/nativo) e GPU, grava `stack.env` e oferece rodar o setup |

Cada componente é opt-in (`Y/N` interativo). Flags: `--yes` (não-interativo), `--dry-run`, `--minimal` (só commands), `--uninstall`, `--debug`, `--help`.

```bash
# Alternativa manual (sem installer)
bash _bootstrap/agentic/stack.sh setup                             # opcional (docker ou nativo)
bash tests/run-all.sh                                              # validação
```

Para personalizar (preencher identidade, criar primeiro projeto) após o install: siga [`guia-personalizacao.md`](guia-personalizacao.md).

---

## Primeiros 30 minutos

### Min 1-5 — Preencher identidade

Abra [`AGENTS.md`](AGENTS.md), vá até a **Seção 2 — Identidade**, substitua os placeholders `<preencher>` com seu nome, área, papel, objetivo, stack. O contrato agêntico passa a refletir você.

### Min 5-10 — Criar primeiro projeto

```bash
cp -r _knowledge/projects/_template _knowledge/projects/meu-projeto
```

Edite cada arquivo dentro (`modules.md`, `integrations.md`, `gotchas.md`, `decisions.md`, `roadmap.md`, `state.md`, `work-log.md`, `meu-projeto.md`) seguindo o guia em [`_prompts/01-onboarding-novo-projeto.md`](_prompts/01-onboarding-novo-projeto.md).

### Min 10-15 — (Opcional) Subir o stack semântico

```bash
bash _bootstrap/agentic/stack.sh setup
bash .claude/scripts/sb-reindex.sh
```

Detalhes, trade-offs e fallbacks por comando: [`_bootstrap/agentic/README.md`](_bootstrap/agentic/README.md).

### Min 15-20 — Validar com comandos básicos

No Claude Code (dentro do diretório do vault):

```
/focus meu-projeto
```

Deve carregar contexto mínimo do projeto. Sem erros = setup OK.

```
/braindump testando o vault no primeiro dia
```

Cria entrada em `_sessions/`.

### Min 20-25 — Capturar primeira decisão

```
/justify "Decidi adotar PostgreSQL ao invés de MongoDB para o write side porque..."
```

Claude busca precedentes em `_decisions/`, valida a proposta, e oferece criar um ADR formal.

### Min 25-30 — Fechar a sessão

```
/end-session meu-projeto
```

Atualiza `_memory/current-state.md`, registra entrada em `_memory/activity-log.md`, escreve `work-log.md` do projeto, captura learnings em `_learnings/` e decisões em `_decisions/`. **Daqui em diante o vault sempre sabe onde você parou.**

### Rotina daily após o primeiro dia

| Quando | Comando | O que faz |
|---|---|---|
| Manhã | `/daily-briefing` | Resumo de projetos ativos, decisões recentes, séries de conteúdo pendentes |
| Antes de mergulhar | `/focus <projeto>` | Carrega contexto mínimo de um projeto específico |
| Captura rápida | `/braindump <texto>` | Salva ideia, conecta ao vault |
| Decisão | `/justify <proposta>` | Valida precedente antes de propor ao humano |
| Fim de sessão | `/end-session <projeto>` | Consolida memória |
| Segunda-feira | `/weekly-review` | Revisão semanal |

---

## Os 39 slash commands

Cada comando tem versão Claude (`.claude/commands/<nome>.md`) e Codex (`.codex/skills/sb-<nome>/SKILL.md`). Agrupados por etapa do AI-SDLC.

### 🎯 Onboarding e contexto

| Comando | O que faz | Quando usar | Por que existe |
|---|---|---|---|
| `/focus <projeto>` | Carrega contexto mínimo (state + gotchas + últimas 3 entradas de work-log) | Ao começar a trabalhar em um projeto | Evita carregar o vault inteiro; mantém janela <40% ocupada |
| `/guide` | Apresenta os comandos disponíveis e quando usar cada um | Quando esquece qual comando rodar | Documentação acionável dentro do próprio runtime |

### 📥 Captura e ingestão

| Comando | O que faz | Quando usar | Pros / Contras |
|---|---|---|---|
| `/braindump <texto>` | Captura ideia bruta, categoriza, conecta ao vault via WikiLinks, propõe destino (`_learnings/`, `_decisions/`, `_pipeline/`) | Pensamento solto que não pode escapar | **+** Zero fricção; **−** Pode gerar entradas órfãs se não revisar |
| `/ingest <url-ou-texto>` | Lê fonte externa, sumariza, salva em `_sources/` com frontmatter completo | Artigo/vídeo/podcast que vai embasar decisão | **+** Centraliza fontes; **−** Sem stack semântico, perde recall futuro |
| `/review-captures` | Processa inbox auto-captures, promove para destino canônico ou arquiva | Quando inbox de hooks acumula | **+** Mantém inbox sob controle; **−** Manual (não automatizado) |

### 🔍 Busca e Q&A

| Comando | O que faz | Quando usar | Pros / Contras |
|---|---|---|---|
| `/ask <pergunta>` | Resposta sintetizada via busca semântica + leitura de fontes, sempre com referências verificáveis | Pergunta sobre conteúdo do vault | **+** Recall semântico; **−** Requer stack ativo para qualidade plena (fallback grep) |
| `/search <query>` | Top-K resultados via Qdrant + filtros (kind, project, k) | Procurar referência específica | **+** <100ms; **−** Sem stack, vira grep |
| `/reindex` | Reindex incremental ou completo do Qdrant | Após mudanças grandes no vault | **+** Mantém index fresco; **−** Requer stack ativo |
| `/recall <query>` | **Recall associativo**: sementes semânticas + propagação pelas sinapses (links tipados com peso) + força de uso; cada resultado explica a cadeia de memórias | Quando o contexto AO REDOR dos hits importa (decisão → gotcha → projeto) | **+** Memória puxa memória, explicável; **−** Modo query requer stack (modo `--seed` é offline) |
| `/consolidate` | Ciclo de "sono" da memória: compacta current-state, expira capturas, propõe merges/links aprendidos, reconcilia grafo FalkorDB | Semanal (cron) ou quando a memória de trabalho crescer | **+** Estanca memory rot sem apagar nada; **−** Propostas exigem curadoria humana |

### ⚖️ Decisão e justificação

| Comando | O que faz | Quando usar | Pros / Contras |
|---|---|---|---|
| `/justify <proposta>` | Busca precedentes em `_decisions/` + `_learnings/`, valida proposta, sugere alinhamento com ADR existente | Antes de propor decisão estratégica ao humano | **+** Evita ADRs contraditórios; **−** Vault vazio = sem precedente |
| `/rfc <tema>` | Gera draft de RFC/design doc estruturado em `_pipeline/` | Mudança grande que precisa formalização | **+** Padroniza propostas; **−** Boilerplate inicial pode ser excessivo |
| `/tech-research <tecnologia>` | Avalia tecnologia com rigor (maturidade, comunidade, alternativas) antes de adotar | Antes de adicionar dependência nova | **+** Reduz adoção impulsiva; **−** Tempo para rodar |

### 📝 Pipeline editorial

| Comando | O que faz | Quando usar | Pros / Contras |
|---|---|---|---|
| `/content-idea <tema>` | Gera 3-7 ideias de conteúdo baseadas no SEU material real (não genérico) | Pauta editorial | **+** Ideias ancoradas; **−** Requer `_content/persona.md` para qualidade |
| `/article-draft <rascunho>` | Valida, cura, registra artigo longo em `_content/articles/` com frontmatter | Publicar artigo no blog/LinkedIn longform | **+** Garante voz consistente; **−** Sem persona, output genérico |
| `/post-draft <rascunho>` | Idem para posts curtos de feed (150-300 palavras) | Post LinkedIn/X | **+** Liga ao artigo via frontmatter; **−** Idem |
| `/style-profile` | Gera fingerprint estatístico do seu estilo a partir de `_content/articles/` | Quando quer "treinar" a voz | **+** Empírico, não opinião; **−** Precisa de 10+ artigos para sinal |

### 📅 Ritmo diário e semanal

| Comando | O que faz | Quando usar | Pros / Contras |
|---|---|---|---|
| `/daily-briefing` | Briefing matinal: projetos ativos, prioridades, séries de conteúdo pendentes | Início do dia | **+** Reorienta rápido; **−** Pode ficar genérico se `_memory/` está stale |
| `/weekly-review` | Reflexão semanal: feito, pendente, insights, ajustes | Sextas ou segundas | **+** Cadência de cura; **−** Skip-fado é fácil |
| `/end-session <projeto>` | Consolida sessão: atualiza memória, registra decisões/learnings, dispara hooks | Final de sessão produtiva | **+** Memória persistente; **−** Esquecer = vault desatualiza |
| `/session-handoff` | Gera `HANDOFF.md` para retomada em próxima sessão (efêmero) | Antes de sair sem fechar | **+** Salva contexto perdido; **−** É efêmero (gitignored) |

### 🧭 Navegação e priorização

| Comando | O que faz | Quando usar | Pros / Contras |
|---|---|---|---|
| `/beacon` | Cruza vault + projeto (CWD): aponta UMA próxima ação proporcional | Quando não sabe o que fazer agora | **+** Decisão única; **−** Vault vazio = sem sinal |
| `/pipeline` | Dashboard de projetos/tasks ativos | Visão portfólio | **+** Visão consolidada; **−** Precisa `_pipeline/` populado |

### 🚀 Pipeline de entrega

| Comando | O que faz | Quando usar | Pros / Contras |
|---|---|---|---|
| `/completion-audit` | Audita escopo declarado vs entregue, listando gaps | Antes do PR | **+** Pega scope creep; **−** Pode ser excessivo em fix triviais |
| `/delivery-closeout` | Fecha entrega: git status, PR/merge/tag/docs/capturas | Após merge | **+** Garante housekeeping; **−** Pesado para entregas pequenas |
| `/live-deploy-validate` | Valida deploy em ambiente real (smoke + golden path) | Pós-deploy crítico | **+** Detecta regressão prod; **−** Requer ambiente acessível |
| `/ux-product-audit` | Audita UX/produto contra critérios definidos | Features visíveis ao usuário | **+** Estende code review para UX; **−** Subjetivo |

### 🩺 Métricas e saúde do vault

| Comando | O que faz | Quando usar | Pros / Contras |
|---|---|---|---|
| `/lint` | Audita saúde do knowledge graph e reporta defeitos | Semanal (já cronado) | **+** Detecta drift; **−** Vault vazio = vazio |
| `/graph-metrics` | Métricas do grafo (broken links, ilhas, hubs) | Quando suspeita de drift de links | **+** Diagnóstico cirúrgico; **−** Output numérico precisa interpretação |
| `/tag-audit` | Auditoria de tags fora da taxonomia | Quando tags proliferam | **+** Mantém taxonomia limpa; **−** Manual |

### 🔧 Densificação e refactor de notas

| Comando | O que faz | Quando usar | Pros / Contras |
|---|---|---|---|
| `/densify <path>` | Aumenta densidade de links em arquivos específicos via similaridade | Notas órfãs detectadas pelo lint | **+** Reduz silos; **−** Requer stack semântico |
| `/consolidate-prompts` | Consolida `_memory/.prompt-log.txt` em sinais agregados | Quando log fica grande | **+** Aprendizado meta; **−** Requer Python |
| `/curate-vault` | Apresenta propostas do self-curation agent + registra decisão humana | Após `/learn-loop` ou cron | **+** Cura assistida; **−** Requer curator agentic |

### 🤖 AI-SDLC avançado

| Comando | O que faz | Quando usar | Pros / Contras |
|---|---|---|---|
| `/dev-squad [resume <run-id>]` | **Planejamento em Opus + execução paralela em Sonnet/Haiku em worktrees isolados.** 1 task = 1 commit; 1 wave = 1 PR. Standalone em qualquer projeto. | Mudanças com 5+ tasks paralelizáveis | **+** Paralelismo real; **−** Custo de API multiplicado |
| `/predict <projeto>` | Sugere próximas tasks via heurísticas + Claude (se `ANTHROPIC_API_KEY`) | Após `/end-session` | **+** Reduz "qual o próximo passo"; **−** Fallback determinístico modesto |
| `/learn-loop` | Loop observacional: gera candidatos a evolução de skills/commands/hooks | Mensal ou quando bateu skill ruim | **+** Skills evoluem; **−** Requer revisão humana |
| `/skill-evolve <skill>` | Aplica melhoria validada de skill (consome candidato do learn-loop) | Após learn-loop produzir candidato aprovado | **+** Evolução sistemática; **−** Pode regredir se A/B mal feito |

### 🏛️ Governança e cores

| Comando | O que faz | Quando usar | Pros / Contras |
|---|---|---|---|
| `/core-session [projeto\|new]` | Analisa core drift, gera checklist de derivação, ou relatório completo de candidatos a promoção | Quando mantém core repos compartilhados | **+** Mantém cores alinhados; **−** Só útil com 3+ projetos consumindo cores |

### 🧠 Engenharia de contexto

| Comando | O que faz | Quando usar | Pros / Contras |
|---|---|---|---|
| `/context-compression` | Comprime contexto preservando decisões críticas | Janela ocupada >70% | **+** Estende sessão útil; **−** Pode perder nuance |
| `/context-engineering` | Estrutura carregamento de contexto em 5 camadas | Início de sessão complexa | **+** Carga mínima; **−** Curva inicial |

---

## Paridade Claude ↔ Codex

Os 37 comandos têm **port equivalente em Codex** em `.codex/skills/sb-<comando>/`. O `tests/test-codex-parity.sh` valida:

- Cada `.claude/commands/<cmd>.md` tem `.codex/skills/sb-<cmd>/SKILL.md` correspondente
- Frontmatter YAML do SKILL.md tem `name: sb-<cmd>` e `source_command: ".claude/commands/<cmd>.md"`
- Existe `agents/openai.yaml` para integração nativa OpenAI/Codex

**Skills nativas adicionais** em `.claude/skills/` (não têm equivalente em comando):
- `beacon` — versão skill da navegação
- `context-compression`, `context-engineering` — meta-skills de contexto
- `dev-squad` — orquestração multi-agente (Opus + Sonnet + Haiku)
- `session-handoff` — handoff entre sessões

---

## Stack semântico opcional (Qdrant + Ollama)

**TL;DR**: 2 comandos sobem o stack (docker ou nativo, conforme `stack.env`); `/ask`, `/search`, `/justify`, `/densify`, `/learn-loop` ganham qualidade semântica.

```bash
bash _bootstrap/agentic/stack.sh setup
bash .claude/scripts/sb-reindex.sh
```

### Por que adotar

- **Recall semântico**: `"como tratamos idempotência"` recupera `_decisions/redis-idempotency-keys.md` mesmo sem "idempotency" na query
- **Local-first**: nada sai da máquina; embeddings via Ollama, índice em Qdrant local
- **Sem custo recorrente**: zero API key, zero billing
- **Determinístico**: mesma query = mesmos top-K

### Trade-offs

| | Com stack | Sem stack |
|---|---|---|
| Setup | Docker + ~3GB disco + ~512MB RAM idle | Zero |
| Recall | Semântico (sinônimos, paráfrases) | Só keyword via grep |
| Performance | <100ms por query | Grep nativo (lento em vaults grandes) |
| Custo | Zero recorrente | Zero |

### Subsistemas Python adicionais (em `_bootstrap/agentic/`)

| Módulo | Função | Externa? |
|---|---|---|
| `indexer/` | Chunking + embeddings + push para Qdrant | Qdrant + Ollama |
| `eval/` | Benchmark de qualidade do retrieval | — |
| `curator/` | Heurísticas H1-H7 de curadoria do vault | Standalone |
| `predictor/` | Sugestões de próximas tasks via LLM + heurísticas | Anthropic API opcional |
| `style/profiler.py` | Style profiler empírico para `/style-profile` | — |

Documentação completa, fallbacks por comando, alternativas consideradas e setup de GPU: **[`_bootstrap/agentic/README.md`](_bootstrap/agentic/README.md)**.

---

## Governança e hooks

### Hooks Claude Code (em `.claude/settings.json`)

Executam automaticamente, sem você precisar lembrar:

| Hook | Dispara em | Script | O que faz |
|---|---|---|---|
| `UserPromptSubmit` | Cada prompt | `on-prompt-submit.sh` | Detecta pendências (flags de sessão); injeta aviso silencioso. Dispara 1x/dia/projeto. |
| `SessionEnd` | Encerramento de sessão | `on-session-end.sh` | Append `session-end` no activity-log; cria flag `.needs-end-session` se `/end-session` não rodou |
| `PreCompact` | Antes da compactação | `on-pre-compact.sh` | Snapshot crítico (Next Steps + Open Questions) em `.pre-compact-notes.md` |
| `Notification` | Operação longa concluída | `on-notification.sh` | Toast Windows / bell fallback |
| `PostToolUse` | Após Write/Edit/MultiEdit | `on-post-tool-use.sh` | Validação leve de frontmatter |

### Crons opcionais (em `_bootstrap/git-hooks/install.sh`)

Você decide se quer ativar:

| Cron | Frequência | O que faz |
|---|---|---|
| `daily-heartbeat` | 07:00 | Verifica staleness do vault; escreve `_memory/heartbeat-latest.md` |
| `weekly-vault-lint` | Segunda 09:00 | Lint completo; alerta se crítico |
| `weekly-core-session` | Segunda 09:32 | Conta candidatos no `promotion-backlog`; alerta drift |

### Contrato agêntico durável

[`AGENTS.md`](AGENTS.md) define **o contrato de memória obrigatório** para qualquer agente operando neste vault (Claude, Codex, Antigravity, runtimes equivalentes):

1. Carregar contexto mínimo antes de trabalho produtivo
2. Consultar second-brain antes de pedir decisão humana
3. Registrar planos relevantes em `_pipeline/` ou `/rfc`
4. Deixar rastro estruturado em `work-log.md`, `state.md`, `_memory/`, `_learnings/`, `_decisions/`
5. Rodar `/delivery-closeout` em entregas e `/end-session` em toda sessão produtiva
6. Capturas automáticas em `_pipeline/inbox/` não são canônicas até revisão
7. Buscar precedente antes de criar ADR/learning/pattern
8. Nunca registrar prompts brutos, segredos, tokens ou PII

Resposta final após trabalho produtivo deve declarar exatamente um destes status: `vault: atualizado`, `vault: pendente` ou `vault: nao aplicavel`.

---

## Testes e lint

```bash
bash tests/run-all.sh
```

| Suite | O que valida | Pros / Contras |
|---|---|---|
| `shell-syntax` | `bash -n` em todos scripts | **+** Rápido (<1s); **−** Não pega lógica |
| `structure` | Diretórios e arquivos críticos presentes | **+** Detecta scaffold quebrado; **−** Não valida conteúdo |
| `frontmatter` | YAML válido em notas críticas | **+** Pega frontmatter quebrado; **−** Só toca 8 arquivos |
| `template-completeness` | Template de projeto tem todos os 9 arquivos | **+** Garante onboarding novo projeto | |
| `lint-pre-donate` | Guard de IP-leak; bloqueia paths privados, nomes internos, hostnames | **+** Crítico para publicar; **−** Falso positivo no próprio fixture |
| `workflow-commands` | Comandos canônicos presentes | **+** Detecta delete acidental | |
| `learn-loop` | Smoke test do observational learn-loop | **+** Valida pipeline meta-skill; **−** Requer Python |
| `codex-parity` | Paridade 1:1 Claude ↔ Codex (37/37) | **+** Crítico; **−** Falha em ambiente sem Codex global |
| `secret-guard` | Hook anti-secret captura tentativas | **+** Crítico para segurança; **−** Requer Python |
| `assisted-hooks` | Hooks de contexto disparam corretamente | **+** Valida automação; **−** Requer Python |

### Lint anti-IP-leak

```bash
bash .claude/scripts/lint-pre-donate.sh .
```

Detecta paths privados absolutos da sua organização, nomes internos de cliente/projeto, hostnames internos (padrões tipo `node-XX`, faixas IP privadas), stack pesada não documentada, frontmatter com tags privadas. Output bloqueante: doação interrompida com motivo até resolução. Patterns exatos estão hardcoded em `.claude/scripts/lint-pre-donate.sh` — adapte ao escopo da sua organização.

---

## Como difere de outras opções

| | Obsidian (plano) | Notion AI | `second-brain-starter` | **`second-brain-premium`** |
|---|---|---|---|---|
| Memória entre sessões | manual | parcial | ✅ | ✅ |
| Slash commands | — | — | 12 | **37** |
| Paridade Claude+Codex | — | — | parcial | **1:1** |
| Busca semântica local | — | — | — | **Qdrant + Ollama** |
| Dev-squad multi-agente | — | — | — | **Opus + Sonnet + Haiku** |
| Pipeline de entrega | — | — | — | **closeout + audit + validate** |
| Biblioteca de padrões | — | — | — | **`_patterns/` + `_features/`** |
| Lint anti-IP-leak | — | — | — | **guarda automatizado** |
| Contrato agêntico durável | — | — | leve | **AGENTS.md formal** |
| 100% local (markdown) | ✅ | ❌ | ✅ | ✅ |
| Open Source | ✅ | ❌ | MIT | privado |

---

## Filosofia

Quatro princípios:

1. **Compilar conhecimento na ingestão.** Não fazer o agente re-ler os mesmos documentos a cada pergunta. Padrão herdado do [LLM Wiki do Karpathy](https://x.com/karpathy/status/1808509395268559074).

2. **Continuidade de sessão é infraestrutura.** Hooks e crons mantêm estado vivo — você não precisa lembrar de rodar nada.

3. **Paridade entre agentes é durável.** Comandos Claude e skills Codex evoluem juntos. Quando um lado muda, o outro precisa mudar antes do merge (test-codex-parity bloqueia).

4. **Decisões precisam de precedente.** `/justify` força consulta ao vault antes de qualquer ADR novo. Decisões contraditórias são detectadas pelo curator (H6).

---

## Estrutura do repositório

```
AGENTS.md                          <- contrato agêntico durável (entrada principal)
CLAUDE.md                          <- ponte de compatibilidade Claude Code
START-HERE.md                      <- onboarding em 5 passos
guia-instalacao.md                 <- setup técnico passo a passo
guia-personalizacao.md             <- como adaptar o scaffold a você
README.md                          <- este arquivo

_knowledge/
  projects/
    _template/                     <- copie para criar cada projeto
    <projeto>/                     <- seus projetos (vazio no scaffold)

_bootstrap/
  agentic/                         <- stack Qdrant + Ollama (opcional)
    stack.sh                       <- setup/start/stop/status (modo docker ou nativo)
    docker-compose.yml             <- containers (modo docker)
    docker-compose.gpu.yml         <- override GPU NVIDIA (SB_STACK_GPU=on)
    README.md                      <- por que e como usar
    indexer/, eval/, curator/, predictor/, style/   <- subsistemas Python
  templates/                       <- templates de projeto/decision/state
  git-hooks/                       <- post-commit, post-merge, install.sh

_prompts/                          <- prompts reutilizáveis (15 prompts)

_memory/                           <- runtime state (vazio no scaffold)
_pipeline/                         <- planos, RFCs, inbox (vazio no scaffold)
_sessions/                         <- braindumps, session logs (vazio no scaffold)
_learnings/                        <- aprendizados cross-cutting (vazio no scaffold)
_decisions/                        <- ADRs cross-project (vazio no scaffold)
_sources/                          <- fontes ingeridas via /ingest (vazio no scaffold)
_content/                          <- pipeline editorial (vazio no scaffold)
_index/                            <- catálogos regeneráveis (vazio no scaffold)
_patterns/                         <- biblioteca de padrões (vazio no scaffold)
_features/                         <- features reutilizáveis (vazio no scaffold)
_cores/                            <- core repos compartilhados (vazio no scaffold)
_infrastructure/                   <- estado operacional (vazio no scaffold)

.claude/
  commands/                        <- 39 slash commands
  scripts/                         <- 30 scripts (hooks, lint, lib)
  skills/                          <- 5 skills nativas (beacon, dev-squad, etc.)
  settings.json                    <- hooks Claude Code

.codex/
  skills/sb-*/                     <- 37 ports Codex paritárias

.specs/decisions/                  <- ADRs de governança do framework
tests/                             <- 11 suites de validação
.github/workflows/ci.yml           <- CI Premium Gold (shellcheck + tests)
pyproject.toml                     <- config ruff + mypy
.gitignore                         <- ignora flags efêmeras, node_modules, etc.
```

Cada `_*/` tem `README.md` próprio explicando propósito, formato esperado e quais comandos populam.

---

## FAQ

### Preciso ser desenvolvedor?

Sim — diferente do starter, o premium assume familiaridade com Git, terminal, Docker (opcional) e ciclo SDLC. Comandos como `/delivery-closeout`, `/rfc`, `/dev-squad` fazem sentido em contexto de engenharia.

### Preciso pagar pela API?

Sim, se for usar Claude Code: conta Anthropic com créditos ou assinatura Claude Pro/Max. Codex tem modelo próprio. Sem assinatura, scaffold ainda é útil como knowledge base (markdown nativo), mas você perde os 37 comandos.

### Qual a diferença vs `second-brain-starter`?

| Aspecto | Starter | Premium |
|---|---|---|
| Foco | Uso pessoal | Enterprise / portfolio |
| Skills | 12 | 37 |
| Paridade Codex | parcial | 1:1 |
| Stack semântico | — | Qdrant + Ollama opcional |
| Dev-squad | — | ✅ |
| Pipeline editorial | leve | completo (article + post + style profile) |
| Pipeline de entrega | — | ✅ (closeout + audit + validate) |
| Padrões/Features | — | ✅ (libs vazias com guia) |
| Multi-agente install | `install.sh --agent=` | manual (clone + use) |
| Licença | MIT | privado |

### Posso usar sem Docker?

Sim. Stack Qdrant+Ollama é opcional. Todos os comandos que dependem dele degradam para fallback determinístico. Você perde recall semântico, mas mantém ~80% das capacidades.

### Posso integrar com Cursor / Gemini CLI?

Parcialmente. O contrato em `AGENTS.md` é portável (qualquer agente que lê AGENTS.md respeita o protocolo). Slash commands específicos de Claude Code não rodam fora dele, mas o conteúdo de `.claude/commands/<cmd>.md` é prompt legível por qualquer LLM. Adaptadores específicos para Cursor/Antigravity são roadmap futuro.

### Meu vault é versionável em git?

Sim. `.gitignore` ignora apenas estado runtime efêmero (`_memory/.flag-*`, `_memory/.prompt-log.txt`, `_memory/.events/`, `.claude/scheduled_tasks.lock`, `HANDOFF.md`, `SESSION-CHECKPOINT.md`). Tudo o que vale ser preservado é commitável.

### Como atualizo o scaffold sem perder meus dados?

Os diretórios `_knowledge/projects/<seu-projeto>`, `_memory/*` (exceto `.flag`), `_decisions/*.md`, `_learnings/*.md`, `_sources/*.md`, `_content/*.md` são seus. Os arquivos do framework (`.claude/`, `.codex/`, `_bootstrap/`, `tests/`, `AGENTS.md`, `CLAUDE.md`, `START-HERE.md`, `guia-*.md`) podem ser atualizados via merge/rebase contra novas releases.

### Posso publicar partes do meu vault como OSS?

Sim. Rode `bash .claude/scripts/lint-pre-donate.sh <arquivo-ou-diretorio>` antes de publicar. O guard bloqueia paths privados, nomes internos, hostnames, frontmatter com tags privadas.

---

## Troubleshooting

### "command not found: bash" no Windows

Instale [Git for Windows](https://git-scm.com/download/win) (vem com Git Bash).

### Skills Codex `sb-*` não aparecem

Verifique se `.codex/skills/sb-<cmd>/SKILL.md` existe e tem `name: sb-<cmd>` no frontmatter. Rode `bash tests/test-codex-parity.sh` para diagnóstico estrutural.

### Hooks Claude não disparam

Confirme entradas em `.claude/settings.json`. Reinicie sessão Claude Code. Garanta que scripts são executáveis: `chmod +x .claude/scripts/*.sh`.

### Stack Qdrant/Ollama não sobe

```bash
bash _bootstrap/agentic/stack.sh status
# modo docker:
docker compose -f _bootstrap/agentic/docker-compose.yml logs
# modo nativo:
cat _bootstrap/agentic/native/run/*.log
```

Causas comuns: porta 6333/11434 já em uso, Docker daemon parado (modo docker), espaço em disco insuficiente.

### Test `secret-guard` ou `assisted-hooks` falham

Requerem Python 3.11+ no PATH. Sem Python, esses testes ficam vermelhos mas o resto do framework funciona. Instale via [python.org](https://www.python.org/downloads/) ou `brew install python@3.11`.

### Test `codex-parity` mostra "runtime global ausente"

Esperado em ambientes sem Codex CLI instalado. A validação estrutural (lib equivalente em disco) passa; só falha o diff contra `~/.codex/skills/`. Não é regressão.

### Lint reporta violações que parecem falsas

Os 3 hits esperados em `lint-pre-donate.sh` (linhas 45, 108) e `tests/test-lint-pre-donate.sh:34` são by-design — são os patterns que o lint procura. Qualquer outro hit é real.

---

## Licença

Repositório privado. Sem LICENSE file. Uso interno.

Para versão OSS (MIT), use [`second-brain-starter`](https://github.com/marciohideaki/second-brain-starter).

---

## 🇬🇧 English summary

### What this is

A premium, enterprise-grade second-brain scaffold derived from the open-source [`second-brain-starter`](https://github.com/marciohideaki/second-brain-starter). Designed for engineers, architects, and teams practicing AI-SDLC who need persistent memory across sessions, formal decision governance, and parallel-project workflows.

### What's different vs starter

- **39 slash commands** (vs starter's 12) covering capture → ingest → decide → execute → validate → deliver → close
- **1:1 Claude ↔ Codex parity** (37 ports in `.codex/skills/sb-*/`)
- **Optional local semantic stack** (Qdrant + Ollama) for `/ask`, `/search`, `/justify`, `/densify`
- **Dev-squad** for parallel multi-agent execution (Opus planning + Sonnet/Haiku workers in isolated worktrees)
- **Editorial pipeline** (`/article-draft`, `/post-draft`, `/style-profile`)
- **Delivery pipeline** (`/completion-audit`, `/delivery-closeout`, `/live-deploy-validate`, `/ux-product-audit`)
- **Pattern/feature library** scaffolding (`_patterns/`, `_features/`, `_cores/`)
- **IP-leak lint** (`lint-pre-donate.sh`) — blocks private paths, internal names, hostnames before publish
- **Durable agentic contract** in [`AGENTS.md`](AGENTS.md) — mandatory protocol any agent must follow

### Install

```bash
git clone https://github.com/HideakiSolutions/second-brain-premium.git
cd second-brain-premium
./install.sh                  # interactive installer (recommended)

# Or manual:
bash _bootstrap/agentic/stack.sh setup                             # optional semantic stack (docker or native)
bash tests/run-all.sh
```

The installer is **agnostic** (zero hardcoded paths) and **idempotent** (re-run safely). It asks for each destination, backs up any external file before modifying, never uses `sudo`. Flags: `--yes`, `--dry-run`, `--minimal`, `--uninstall`, `--debug`, `--help`.

### Quick start

1. Fill in identity in [`AGENTS.md`](AGENTS.md) Section 2.
2. Copy `_knowledge/projects/_template` to your first project folder.
3. Run `/focus <project>` and `/end-session <project>` to validate the runtime.
4. (Optional) Bring up Qdrant+Ollama for semantic search — see [`_bootstrap/agentic/README.md`](_bootstrap/agentic/README.md).

### Stack opt-in trade-offs

| | With stack | Without stack |
|---|---|---|
| Setup | Docker + ~3GB disk + ~512MB RAM idle | Zero |
| Recall | Semantic (synonyms, paraphrases) | Keyword grep only |
| Performance | <100ms per query | Native grep |
| Cost | Zero recurring | Zero |
| Privacy | 100% local | 100% local |

Full details, command-level fallbacks, alternatives considered, GPU setup: **[`_bootstrap/agentic/README.md`](_bootstrap/agentic/README.md)**.

### Documentation entry points

- [`AGENTS.md`](AGENTS.md) — agentic contract (read first)
- [`START-HERE.md`](START-HERE.md) — operational onboarding
- [`guia-instalacao.md`](guia-instalacao.md) — installation guide (PT-BR)
- [`guia-personalizacao.md`](guia-personalizacao.md) — personalization guide (PT-BR)
- [`_bootstrap/agentic/README.md`](_bootstrap/agentic/README.md) — semantic stack deep dive
- Each `_*/README.md` — directory-specific purpose, format, populating commands

### License

Private repository. No LICENSE file. For OSS (MIT), see [`second-brain-starter`](https://github.com/marciohideaki/second-brain-starter).
