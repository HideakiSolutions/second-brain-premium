# `_learnings/` — Aprendizados Reutilizáveis

Notas cross-cutting: gotchas, padrões, standards, post-mortems. Tudo que vale ser relembrado em projetos futuros.

## Formato

Frontmatter:
```yaml
---
tags: [learning, <categoria>]
status: active
created: YYYY-MM-DD
related: [[outro-learning]]
---
```

Seções recomendadas:
- **Contexto** — onde apareceu
- **O aprendizado** — frase única
- **Por que importa** — impacto
- **Como aplicar** — passos
- **Related** — WikiLinks

## Origem

- Populado por `/end-session` quando uma sessão produz insight relevante
- Também escrito manualmente quando você quer documentar um gotcha agudo

## Convenções

- Nome de arquivo: kebab-case descritivo (`alembic-linearization.md`, `git-rebase-vs-merge.md`)
- Um learning por arquivo — se virar grande demais, quebrar em sub-learnings linkados
- Diretório nasce vazio; popula com o uso
