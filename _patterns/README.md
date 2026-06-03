# `_patterns/` — Biblioteca de Padrões Arquiteturais

Camada 2A do knowledge graph: padrões reutilizáveis (DDD, hexagonal, CQRS, event-sourcing, saga, outbox, multi-tenancy, idempotency, etc.) **documentados no contexto do seu portfólio**.

## Quando adicionar um padrão

Quando você usa o mesmo princípio arquitetural em 2+ projetos e quer:
- Registrar regras específicas do seu uso (não definições genéricas de livro)
- Linkar para implementações concretas em `_features/`
- Documentar quando NÃO usar
- Ligar a ADRs em `_decisions/`

Use o prompt `_prompts/03-onboarding-novo-padrao.md` como guia para criar uma nota.

## Formato esperado

Frontmatter:
```yaml
---
tags: [pattern, architecture]
status: active
adr: "[[../_decisions/YYYY-MM-DD-titulo]]"   # opcional
created: YYYY-MM-DD
---
```

Seções:
- **What It Solves** — problema concreto, não definição abstrata
- **How It Works Here** — regras específicas do seu portfólio
- **Projects Using This Pattern** — tabela `Projeto | Stack | Notas` com WikiLinks
- **When NOT to Use** — anti-cenários
- **Related Patterns** — WikiLinks para padrões complementares
- **Decision Records** — link para ADR

## Convenções

- Nome: kebab-case (`hexagonal-architecture.md`, `outbox-inbox.md`)
- Cada padrão é referenciado pela `PATTERN-MATRIX.md` em `_index/`
- Diretório nasce vazio; popula com o uso
