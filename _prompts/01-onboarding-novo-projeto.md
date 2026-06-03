# 01 — Como Adicionar Novo Projeto ao Knowledge Graph

Use este prompt quando um novo projeto precisar ser documentado no vault. Cole no Claude Code dentro do diretório `$VAULT`.

---

Adicione o projeto `{NOME_DO_PROJETO}` ao knowledge graph do vault em `$VAULT`.

## 1. Criar estrutura de pastas e arquivos

Crie a pasta `_knowledge/projects/{nome}/` com os seguintes 7 arquivos:

### `{nome}.md` (índice do projeto — substitua `{nome}` pelo nome real do projeto)
```yaml
---
tags: [project-index, wiki, project, {categoria}]
status: active | poc | planned
created: {data}
---
```
Seções obrigatórias (arquivo deve ter < 50 linhas):
- `## What It Is` — descrição em 2-3 frases: o que o projeto resolve e para quem
- `## Quick Stats` — tabela ou lista: Stack, Services/Modules, Phase, Patterns (com WikiLinks para `../../_patterns/`)
- `## Key Reusable Features` — lista das features principais com link para `../../_features/{slug}` e status (production/poc/planned)
- `## How to Run` — comandos mínimos para rodar localmente
- `## Deep Dive` — WikiLinks para: `[[modules]]` · `[[integrations]]` · `[[gotchas]]` · `[[decisions]]` · `[[roadmap]]` · `[[work-log]]`

### `modules.md`
Tabela com todos os módulos/serviços do projeto:
| Módulo | Tier | Stack | Responsabilidade | Feature Principal |
|--------|------|-------|-----------------|------------------|
- Coluna Feature Principal deve linkar para `../../_features/{slug}` quando aplicável
- Se o projeto tem múltiplos tiers ou camadas, documentar a distinção e o motivo

### `integrations.md`
Duas seções:
- `## Dependências Externas` — serviços externos (Keycloak, Kafka, RabbitMQ, Midaz, etc.) com propósito e configuração
- `## Dependências Internas` — outros projetos do portfólio que este projeto consome ou expõe

### `gotchas.md`
Lista de armadilhas, comportamentos não-óbvios e decisões que causariam confusão sem contexto. Mínimo 3 items no formato:
```
### {Título curto}
**Problema:** O que acontece se você não souber isso
**Solução/Contexto:** Como funciona de fato
```

### `decisions.md`
ADRs locais do projeto no formato:
```
### {YYYY-MM-DD} — {Título da Decisão}
**Contexto:** Por que essa decisão foi necessária
**Decisão:** O que foi decidido
**Consequências:** O que mudou, trade-offs
**Reversibilidade:** Fácil / Difícil / Irreversível
```

### `work-log.md`
```yaml
---
tags: [project, work-log]
status: active
created: {data}
---
```
- `> Tipos: epic feature story task fix chore spike session`
- Tabela: `| Data | Tipo | Descrição | Epic ID | Status |`
- Iniciar vazia — o `/end-session` popula automaticamente

### `roadmap.md`
```yaml
---
tags: [project, roadmap]
status: active
---
```
- `## Fase Atual` — o que está em desenvolvimento agora
- `## Próximas Fases` — lista de fases com objetivo e features previstas
- `## Backlog` — features desejadas sem fase definida

---

## 2. Atualizar índices da Camada 0

### `_index/MASTER-INDEX.md`
Adicionar nova linha na tabela de projetos com: nome | domínio | stack resumido | fase | link para README

### `_index/PATTERN-MATRIX.md`
Adicionar nova coluna para o projeto nas linhas dos padrões que ele usa. Valores válidos: `full` | `partial` | `adapted` | `—`

### `_index/FEATURE-CATALOG.md`
Para cada nova feature introduzida pelo projeto, adicionar linha na categoria correta com: Feature | Status | Caminho de implementação | Projetos que usam

---

## 3. (Opcional) Manter índice de portfólio

Se você mantém um índice consolidado de projetos em `_knowledge/projects.md`, adicionar linha na tabela com WikiLink para o novo README. O scaffold não fornece este arquivo por padrão — crie quando tiver 3+ projetos e quiser visão consolidada.

---

## 4. Criar feature pages (se aplicável)

Se o projeto introduz alguma feature reutilizável que outros projetos poderiam aproveitar, criar `_features/{slug}.md` seguindo o prompt `02-onboarding-nova-feature.md`.

Critério: crie feature page se a feature seria consultada por outro dev antes de decidir reimplementar.

---

## 5. Checklist de qualidade

Antes de considerar completo:

- [ ] README tem menos de 50 linhas?
- [ ] Cada módulo em `modules.md` tem link para feature ou padrão quando aplicável?
- [ ] `gotchas.md` tem pelo menos 3 items?
- [ ] `work-log.md` criado (pode estar vazio — será populado pelo `/end-session`)?
- [ ] PATTERN-MATRIX atualizado para o novo projeto?
- [ ] FEATURE-CATALOG atualizado com features novas?
- [ ] WikiLinks bidirecionais: pattern pages apontam de volta para o projeto?

---

## Regras

- Nunca preencher `roadmap.md` com especulação — apenas o que está planejado de fato
- `gotchas.md` é o arquivo mais valioso: documentar o que causaria um bug ou uma semana de investigação
- Links internos sempre em formato `[[../../_patterns/nome|Nome Legível]]` para funcionar no Obsidian
- Não criar arquivo `05-iniciar-sessao-tecnica.md` referenciado em nenhum lugar ainda — use este checklist primeiro
