# `_features/` — Features Reutilizáveis

Camada 2B do knowledge graph: features de produção/POC que podem ser replicadas entre projetos. Diferente de `_patterns/` (princípios), `_features/` documenta **implementações concretas**.

## Quando adicionar uma feature

Quando você implementou algo que vale ser replicado em outro contexto:
- Saga manager, outbox processor, JWT auth flow, multi-tenant header propagation
- Tem contrato claro (input/output)
- Tem implementação localizada (arquivo/módulo específico)

## Formato esperado

Frontmatter:
```yaml
---
tags: [feature, reusable]
status: production | poc | planned
pattern: "[[../_patterns/saga-pattern]]"
projects: [<projeto-1>, <projeto-2>]
created: YYYY-MM-DD
---
```

Seções:
- **What It Is** — descrição em 1 parágrafo
- **Implementation Location** — paths reais (não genéricos) por projeto
- **Core Contract** — assinatura/API, snippets de código
- **How to Reuse** — passos numerados para portar
- **Gotchas** — armadilhas conhecidas
- **Related Patterns** — link para `_patterns/`

## Convenções

- Nome: kebab-case (`orleans-saga-manager.md`, `redis-idempotency-keys.md`)
- Catalogada por `FEATURE-CATALOG.md` em `_index/`
- Diretório nasce vazio; popula com o uso
