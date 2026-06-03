# `_decisions/` — ADRs Cross-Project

Architecture Decision Records que afetam mais de um projeto ou definem governança do vault. Decisões locais de um projeto ficam em `_knowledge/projects/<projeto>/decisions/`.

## Formato

Frontmatter:
```yaml
---
tags: [decision, <area>, <status>]
status: proposed | accepted | superseded
created: YYYY-MM-DD
supersedes: [[outra-decisao]]
---
```

Seções obrigatórias:
- **Contexto** — situação que motivou
- **Decisão** — o que foi decidido
- **Consequências** — trade-offs, o que ganha, o que perde
- **Reversibilidade** — alto/médio/baixo

## Origem

- Populado por `/end-session` quando uma sessão produz decisão estratégica
- Também escrito via `/justify <decisao>` para validar precedente antes de propor
- `/rfc` gera draft que pode virar ADR após aceite

## Convenções

- Nome: `YYYY-MM-DD-slug-decisao.md` (ex.: `2026-06-03-postgres-vs-mysql.md`)
- ADRs aceitos não são editados — superseder cria nova entrada com `supersedes:` apontando para a antiga
- Para ADRs de governança do framework, usar `.specs/decisions/ADR-NNNN-*.md`
- Diretório nasce vazio; popula com o uso
