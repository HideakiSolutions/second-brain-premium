# `_sources/` — Fontes Externas Ingeridas

URLs, artigos, vídeos, podcasts, papers que você quer reusar como base para decisões ou conteúdo. Ingestão via `/ingest <url-ou-texto>`.

## Formato

Frontmatter:
```yaml
---
tags: [source, <tipo>, <tema>]
status: active | archived
created: YYYY-MM-DD
url: https://...
author: <autor>
type: article | video | podcast | paper | tweet | book
---
```

Conteúdo:
- Resumo em 3-5 bullets
- Citações úteis (com âncora)
- Conexões com `_learnings/`, `_patterns/`, `_decisions/` via WikiLinks
- Por que vale lembrar

## Origem

- Comando `/ingest <url>` faz fetch, sumariza e cria o arquivo aqui
- Manual: cole conteúdo bruto e refine

## Convenções

- Nome: `YYYY-MM-DD-slug-fonte.md`
- Não duplicar conteúdo completo — apenas resumo + link
- Diretório nasce vazio; popula com o uso
