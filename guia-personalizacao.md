# Guia de Personalização

Como transformar este scaffold em **seu** second brain. Tempo estimado: 15-30 minutos para setup básico; o vault cresce com o uso.

---

## Pré-requisitos

- Claude Code instalado (ou Codex CLI, se preferir Codex)
- `bash` disponível (Git Bash no Windows, terminal nativo em macOS/Linux)
- `git` para versionar
- **Opcional** (apenas se quiser busca semântica + sugestões via LLM local): Docker + ~6GB de espaço em disco

---

## Passo 1: Preencher sua identidade no `AGENTS.md`

Abra `AGENTS.md` e vá até a **Seção 2 — Identidade**. Substitua os placeholders `<preencher>`:

```markdown
- **Nome:** Seu nome
- **Área de atuação:** O que você faz
- **Papel:** Seu papel atual
- **Objetivo principal:** O que está buscando agora
- **Ferramentas principais:** O que usa no dia a dia
- **LLMs de suporte:** Claude, ChatGPT, Grok, etc.
- **Stack técnico:** Suas tecnologias (linguagens, frameworks, infra)
```

Na **Seção 0 — Regras de idioma**, ajuste se necessário. O padrão é português (BR).

Na **Seção 4 — Guardrails**, revise se há alguma regra que você quer mudar (estilo de escrita, anti-padrões, etc.).

---

## Passo 2: (Opcional) Subir o stack semântico (Qdrant + Ollama)

Esta etapa é **opcional**. O vault funciona sem ela; comandos que dependem do stack semântico degradam para fallback determinístico (grep + Read). Mas se você tem mais de ~100 notas e quer recall por similaridade (não só keyword), vale ligar.

**TL;DR**: rode os 3 comandos abaixo; documentação completa em `_bootstrap/agentic/README.md`.

```bash
docker compose -f _bootstrap/agentic/docker-compose.yml up -d
docker exec sb-ollama ollama pull bge-m3
bash .claude/scripts/sb-reindex.sh
```

Depois, valide:
```bash
bash .claude/scripts/sb-reindex.sh status
```

### Por que adotar

- **Recall semântico**: `/search "como tratamos idempotência?"` recupera a decisão certa mesmo se você não lembra o termo exato — bge-m3 entende sinônimos e paráfrases.
- **Local-first**: nada sai da máquina. Vault e embeddings ficam em containers locais.
- **Sem custo recorrente**: zero API key, zero billing.
- **Determinístico**: a mesma query sempre retorna os mesmos top-K.

### Trade-offs

| | Com stack | Sem stack |
|---|---|---|
| Setup | +Docker, ~3GB disco, ~512MB RAM idle | Zero |
| Recall | Semântico (sinônimos, paráfrases) | Só keyword via grep |
| Manutenção | `/reindex` após mudanças grandes | Nenhuma |
| Privacidade | 100% local | 100% local (igual) |
| Performance | <100ms por query | grep nativo (rápido em vaults pequenos, lento em grandes) |
| Custo | Zero recorrente | Zero |

### Quando NÃO ativar

- Vault com <50 notas (grep resolve)
- Não quer Docker no ambiente
- Máquina restrita (<2GB RAM disponível)

Detalhes completos, fallbacks por comando, alternativas consideradas e setup de GPU: **`_bootstrap/agentic/README.md`**.

---

## Passo 3: Criar seu primeiro projeto

Copie o template:

```bash
cp -r _knowledge/projects/_template _knowledge/projects/meu-projeto
```

Edite cada arquivo dentro de `_knowledge/projects/meu-projeto/`:

| Arquivo | O que preencher |
|---|---|
| `_template.md` | Renomeie para `meu-projeto.md`. Preencha What It Is, Quick Stats, Key Reusable Features, How to Run, Deep Dive |
| `modules.md` | Tabela de módulos/serviços do projeto |
| `integrations.md` | Dependências externas + internas |
| `gotchas.md` | Armadilhas e decisões não-óbvias (mínimo 3) |
| `decisions.md` | Manifesto de decisões locais (ADRs específicos do projeto) |
| `roadmap.md` | Fases, próximos passos |
| `state.md` | Estado atual: branch ativa, próximo passo, bloqueios |
| `work-log.md` | Log de sessões produtivas (vai sendo escrito por `/end-session`) |

Use `_prompts/01-onboarding-novo-projeto.md` como guia detalhado.

---

## Passo 4: Validar o setup

Rode em sequência:

```bash
bash tests/run-all.sh                       # estrutura, paridade, sintaxe
bash .claude/scripts/lint-pre-donate.sh .   # validar que nao tem IP leak
```

Depois, no Claude Code (dentro do diretório do vault):

```
/focus meu-projeto
```

Deve carregar o briefing do projeto sem erros. Se reclamar de arquivo ausente, volte ao Passo 3.

```
/braindump testando o setup do vault
```

Deve criar uma entrada em `_sessions/`.

---

## Passo 5: Consolidar o estado inicial

```
/end-session meu-projeto
```

Isso popula `_memory/current-state.md`, registra entrada em `_memory/activity-log.md`, atualiza `work-log.md` do projeto. A partir daqui o cérebro está operacional.

---

## Dicas

### Adicionar um novo slash command

Crie `.md` em `.claude/commands/` e a skill Codex paritária em `.codex/skills/sb-<nome>/SKILL.md`. Use o `tests/test-codex-parity.sh` para validar.

### Adicionar um padrão arquitetural ao seu portfólio

Use `_prompts/03-onboarding-novo-padrao.md` como guia. O padrão vai em `_patterns/<nome>.md` e pode ser referenciado de qualquer projeto.

### Adicionar uma feature reutilizável

Use `_prompts/02-onboarding-nova-feature.md`. Feature vai em `_features/<nome>.md` linkada ao pattern relevante.

### Atalhos por dia

| Quando | Comando |
|---|---|
| Início do dia | `/daily-briefing` |
| Antes de mergulhar num projeto | `/focus <projeto>` |
| Capturar ideia bruta | `/braindump <texto>` |
| Validar uma decisão | `/justify <proposta>` |
| Fechar uma sessão | `/end-session <projeto>` |
| Fim de semana | `/weekly-review` |

### Hooks automáticos

O scaffold já vem com hooks em `.claude/settings.json`:
- `SessionEnd`: registra encerramento de sessão
- `PreCompact`: preserva contexto antes da compactação
- `UserPromptSubmit`: detecta pendências de sessão
- `PostToolUse`: validações leves após write/edit

Você pode customizar editando `.claude/settings.json`.

### Crons (opcional)

Em `_bootstrap/git-hooks/install.sh` há instruções para registrar crons:
- `daily-heartbeat` (07:00) — verifica staleness do vault
- `weekly-vault-lint` (segunda 09:00) — lint completo
- `weekly-core-session` (segunda 09:32) — relatório de cores compartilhados

---

## Resumo

| Passo | Ação | Tempo |
|---|---|---|
| 1 | Preencher identidade em AGENTS.md | 5 min |
| 2 | (Opcional) Subir Qdrant+Ollama | 5 min |
| 3 | Criar primeiro projeto a partir de `_template/` | 10-15 min |
| 4 | Validar via tests + comando `/focus` | 3 min |
| 5 | Rodar `/end-session` para consolidar | 2 min |

**Total:** 15-30 min. Daí o vault cresce a cada `/end-session`.
