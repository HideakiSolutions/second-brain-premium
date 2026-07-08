# START-HERE — Second Brain Operacional

Este vault é o segundo cérebro operacional do usuário deste repositório.
Ele guarda memória de projetos, decisões, aprendizados, estado de entrega e
fontes reutilizáveis para agentes Claude, Codex e runtimes equivalentes.

## Entrada Autoritativa

- `AGENTS.md` é a fonte durável para agentes.
- `CLAUDE.md` existe por compatibilidade e deve apontar para `AGENTS.md`.
- Regras novas e contratos operacionais devem ser escritos em `AGENTS.md`, não
  em `CLAUDE.md`.
- O contrato completo está em `AGENTS.md`, seção `Contrato Agentico De Memoria`.

## Contrato Curto Para Agentes

Antes de trabalho produtivo:

1. Carregue contexto mínimo com `/focus {projeto}` ou `sb-focus`.
2. Para perguntas, use `/ask`, `/recall` (recall associativo — traz o contexto
   vizinho e a cadeia de memórias) ou `/search` (lookup pontual) antes de
   pedir contexto humano.
3. Para decisões, use `/justify` antes de pedir aprovação ou opinião.
4. Execute e valide com gate proporcional.
5. Em entrega verificável, rode `/delivery-closeout`.
6. Em toda sessão produtiva, rode `/end-session {projeto}`.
7. A resposta final após trabalho produtivo deve conter exatamente um destes
   status: `vault: atualizado`, `vault: pendente` ou `vault: nao aplicavel`.

Fluxo padrão:

```text
focus -> ask/search -> justify -> execute -> validate -> delivery-closeout -> end-session
```

Use `/beacon` ou `sb-beacon` quando precisar escolher a próxima atividade
de um projeto já identificado. Se o projeto não puder ser resolvido, o fallback
oficial é `/pipeline` ou `sb-pipeline`.

## Comandos E Skills

- Comandos Claude: `.claude/commands/*.md`.
- Skills Codex versionadas: `.codex/skills/sb-*`.
- Skills Codex instaladas no runtime global: `/home/annonymous/.codex/skills/sb-*`.
- Scripts compartilhados: `.claude/scripts/*.sh` e `.claude/scripts/lib/*`.

Os comandos e skills têm paridade Claude/Codex. Ao criar ou alterar um comando
operacional, mantenha a skill correspondente e rode a suíte local.

## Stack De Memória

- Camada sináptica: grafo nota-a-nota com pesos, reforço por uso, decay e
  consolidação (`_bootstrap/agentic/synapse/README.md`); recall associativo via
  `/recall`; ciclo de "sono" via `/consolidate` + cron semanal.

- Vault Markdown: fonte humana e rastreável (sempre).
- Qdrant: busca vetorial (opcional — `bash _bootstrap/agentic/stack.sh setup`, modo docker ou nativo).
- Ollama + `bge-m3`: embeddings locais (opcional, casado com Qdrant).
- Scripts `.claude/scripts/`: indexação, busca, densificação, lint e métricas.

## Estrutura Principal

```text
AGENTS.md                         <- entrada neutra e contrato agentico
START-HERE.md                     <- onboarding operacional atual
CLAUDE.md                         <- ponte de compatibilidade

_index/                           <- navegação e catálogos
_knowledge/projects/              <- memória granular por projeto
_cores/                           <- core repos e candidatos a promoção
_patterns/                        <- padrões canônicos
_features/                        <- features reutilizáveis
_memory/                          <- rollup atual, activity log e sinais efêmeros
_pipeline/                        <- planos, inbox e itens ativos
_decisions/                       <- decisões cross-project
_learnings/                       <- aprendizados reutilizáveis
_sources/                         <- fontes externas ingeridas
_infrastructure/                  <- estado operacional de infra

.claude/commands/                 <- comandos Claude
.claude/scripts/                  <- scripts compartilhados
.claude/skills/                   <- skills Claude versionadas quando aplicável
.codex/skills/                    <- skills Codex versionadas
.specs/decisions/                 <- ADRs de governança propostas/aceitas
tests/                            <- validações locais
```

## Validação Rápida

```bash
bash tests/run-all.sh
bash .claude/scripts/sb-reindex.sh status
```

Para mudanças em comandos, skills, hooks, governança ou docs operacionais:

```bash
git diff --check -- START-HERE.md AGENTS.md .claude/commands .codex/skills _knowledge/projects/_template .specs/decisions tests
bash tests/run-all.sh
```

## Quando Usar Cada Fluxo

| Necessidade | Claude | Codex |
|---|---|---|
| Carregar projeto | `/focus {projeto}` | `sb-focus` |
| Responder com fontes | `/ask` ou `/search` | `sb-ask` ou `sb-search` |
| Recall associativo (memória puxa memória) | `/recall` | `sb-recall` |
| Consolidar memória ("sono") | `/consolidate` | `sb-consolidate` |
| Escolher próxima ação | `/beacon` | `sb-beacon` |
| Ver portfolio/funil | `/pipeline` | `sb-pipeline` |
| Validar precedente | `/justify` | `sb-justify` |
| Auditar entrega | `/completion-audit` | `sb-completion-audit` |
| Fechar entrega | `/delivery-closeout` | `sb-delivery-closeout` |
| Fechar sessão | `/end-session {projeto}` | `sb-end-session` |
| Reindexar busca | `/reindex` | `sb-reindex` |

## Regra De Ouro

Nunca opere só com memória de chat. Consulte o vault antes de decidir e atualize
o vault ao encerrar trabalho produtivo.
