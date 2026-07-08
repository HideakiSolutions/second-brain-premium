---
tags: [index, navigation, project, active]
status: active
created: 2026-07-08
updated: 2026-07-08
---

# 🏗️ Projetos — Mapa de Conteúdo

> Memória granular por projeto: uma pasta por projeto, criada automaticamente pelo `/end-session <slug>` na primeira sessão. Esta página explica **como cada pasta funciona**.

## Anatomia de um projeto

| Arquivo | Pergunta que responde | Quem escreve |
|---|---|---|
| `<slug>.md` | O que é este projeto? (hub) | humano + `/end-session` |
| `state.md` | Onde estamos AGORA? (injetado nas sessões) | `/end-session` |
| `roadmap.md` | Para onde vamos? | planejamento |
| `work-log.md` | O que foi feito, quando? (append-only) | `/end-session` |
| `decisions.md` + `decisions/` | O que decidimos localmente? | `/end-session` |
| `gotchas.md` + `gotchas/` | Que armadilhas já pisamos? | `/end-session` |
| `modules.md` · `integrations.md` | Como o código se organiza / com o que fala? | curadoria |

## Como entrar num projeto

- **Humano:** abra o hub `<slug>.md` e siga os links.
- **Agente:** `/focus <slug>` (carrega o mínimo) → `/beacon` (próxima ação).
- **Novo projeto?** `/end-session <slug>` auto-registra a estrutura completa.

## Related

- [[../../HOME|HOME]] · [[../../_index/README|MOC Índices]]
