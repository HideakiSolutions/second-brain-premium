---
tags: [index, navigation, home, active]
status: active
created: 2026-07-08
updated: 2026-07-08
---

# 🧠 HOME — Segundo Cérebro

> [!tip] Como usar esta página
> Este é o ponto de entrada **humano** do vault (fixe esta nota no Obsidian).
> Agentes entram por [[AGENTS|AGENTS.md]] e [[START-HERE]]. Os dois mundos compartilham os mesmos arquivos - cada link daqui também é uma sinapse do grafo.

## 🎯 Onde estou agora

- [[_memory/current-state|Current State]] - rollup recente do portfólio
- [[_memory/synapse-report|Synapse Report]] - último ciclo de consolidação da memória (gerado pelo `/consolidate`)
- [[_memory/graph-metrics|Graph Metrics]] - saúde do grafo (alvo: broken 0 · tags 0)
- [[_pipeline/self-improvement-candidates|Self-Improvement]] - propostas aguardando sua decisão

## 🗺️ Navegação por camada

| | Camada | Entrada |
|---|---|---|
| 📇 | **Índices** (mapa do vault) | [[_index/README\|MOC Índices]] |
| 🏗️ | **Projetos** (memória granular) | [[_knowledge/projects/README\|MOC Projetos]] |
| 📐 | **Patterns** (padrões arquiteturais) | [[_patterns/README\|MOC Patterns]] |
| 🧩 | **Features** (implementações reutilizáveis) | [[_features/README\|MOC Features]] |
| ⚖️ | **Decisions** (ADRs cross-project) | [[_decisions/README\|MOC Decisions]] |
| 🎓 | **Learnings** (aprendizados e guardrails) | [[_learnings/README\|MOC Learnings]] |
| 🧱 | **Cores** (repositórios base) | [[_cores/README\|MOC Cores]] |
| 🛰️ | **Infra** (ambientes, ferramentas) | [[_infrastructure/README\|MOC Infra]] |
| 📰 | **Conteúdo** (artigos, posts, séries) | [[_content/README\|MOC Conteúdo]] |
| 📥 | **Fontes** (ingestões externas) | [[_sources/README\|MOC Fontes]] |
| 🕰️ | **Memória & Sessões** (episódica) | [[_memory/README\|MOC Memória]] · [[_sessions/README\|MOC Sessões]] |

## 💬 Como perguntar ao cérebro

> [!example] Os cinco gestos essenciais
> - **"O que sabemos sobre X?"** → `/recall "X"` (memória puxa memória, com a cadeia)
> - **"Já decidi algo assim?"** → `/justify "proposta"` ou `/recall "..." --kind decisions`
> - **"Me situa no projeto Y"** → `/focus Y`
> - **"O que fazer agora?"** → `/beacon` (projeto) · `/pipeline` (portfólio)
> - **Fechar o dia** → `/end-session` (grava memória + reforça sinapses)

Catálogo completo de comandos: [[AGENTS|AGENTS.md → Mapa de Workflows]] e [[README|README → slash commands]].

## 🕸️ O grafo vivo

No Graph View do Obsidian, use o filtro abaixo para ver só o grafo semântico (sem runtime/logs) e crie grupos de cor por pasta (`path:_patterns`, `path:_decisions`, ...):

```text
-path:.claude -path:.codex -path:.github -path:_bootstrap -path:_memory -path:_prompts -path:_pipeline -path:node_modules
```

A mesma malha, com pesos e reforço por uso, é o que os agentes consultam via `/recall` - detalhes em [[_decisions/2026-07-08-camada-sinaptica-memoria-associativa|ADR Camada Sináptica]] e `_bootstrap/agentic/synapse/README.md`.

> [!info] Convivência humano ↔ IA
> As regras que mantêm as duas otimizações em harmonia (onde emoji/callouts são bem-vindos, o que jamais muda em notas canônicas) estão em [[_index/CONVIVENCIA-HUMANO-IA|Convivência Humano-IA]].

## 🧹 Manutenção (quase toda automática)

| Quando | O quê |
|---|---|
| A cada prompt | Injeção de contexto associativo (hook) |
| A cada leitura/escrita | Ativação sináptica registrada |
| `/end-session` | Vault sincronizado + reforço hebbiano |
| Segunda 09:00-09:45 (crons opcionais) | Lint · core-session · **sono da memória** (decay + consolidação + relatório) |
| Você decide | Propostas do synapse-report e candidatos de evolução |
