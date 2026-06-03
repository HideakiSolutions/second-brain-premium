---
tags: [index, governance, active]
status: active
created: 2026-04-28
updated: 2026-04-28
---

# Bootstrap Templates

Templates obrigatórios para arquivos de projeto em `_knowledge/projects/<projeto>/`.

## Como funcionam

Todo arquivo de projeto deve seguir o template correspondente. Lint (`weekly-vault-lint.sh`) verifica a presença das **seções obrigatórias** detectadas por regex:

- `## Padrões Aplicados` — mínimo 2 links para `_patterns/`
- `## Features Reutilizadas` — mínimo 1 link para `_features/` (apenas em `index` e `modules`)
- `## Decisões Relacionadas` — mínimo 1 link para `_decisions/`
- `## Learnings Capturados` — opcional mas pontuado

## Templates disponíveis

| Template | Tipo de arquivo | Seções obrigatórias |
|---|---|---|
| `project-index.md.tpl` | `<projeto>.md` | Padrões + Features + Decisões |
| `project-state.md.tpl` | `state.md` | Padrões + Decisões |
| `project-decisions.md.tpl` | `decisions.md` | Padrões + Decisões |
| `project-gotchas.md.tpl` | `gotchas.md` | Padrões + Decisões |
| `project-modules.md.tpl` | `modules.md` | Padrões + Features |

## Placeholders

- `{{PROJECT_DISPLAY_NAME}}` — nome legível (ex: "Cambio Real")
- `{{DOMAIN_TAGS}}` — tags da seção 2 da [[../../_index/TAG-TAXONOMY|TAG-TAXONOMY]] (ex: `fintech, forex, compliance`)
- `{{DATE}}` — `YYYY-MM-DD`
- `{{PATTERN_N}}` — slug em `_patterns/` (ex: `cqrs`, `outbox-inbox`)
- `{{FEATURE_N}}` — slug em `_features/`
- `{{ADR_N}}` — slug em `_decisions/`
- `{{LEARNING_N}}` — slug em `_learnings/`
- `{{P_DISPLAY}}` / `{{F_DISPLAY}}` — texto exibido após `|` no WikiLink

## Gold standard

`_knowledge/projects/meu-projeto/meu-projeto.md` é o exemplo canônico — replicar sua densidade de links nos demais.

## Tipos não modelados aqui

- `work-log.md` — formato livre append-only por data, sem requisitos de link mínimo
- `roadmap.md` — formato livre estruturado por fase
- `integrations.md` — formato livre, links emergem naturalmente
- `agents.md`, `skills.md`, `workflows.md`, `servers.md`, `policies.md`, `structure.md` — específicos de hseos/mcp-factory/platform-gitops, sem template fixo
