# `_content/` — Produção Editorial

Artigos longos, posts de feed, séries de conteúdo. Pipeline editorial assistido por `/article-draft`, `/post-draft`, `/content-idea`.

## Estrutura

| Caminho | Função |
|---|---|
| `persona.md` | Voz, tese dominante, padrão de pensamento, tom (lido por `/article-draft` e `/post-draft`) |
| `themes.md` | Temas cobertos e gaps |
| `ideas-backlog.md` | Ideias geradas por `/content-idea` |
| `articles/YYYY-MM-DD-slug.md` | Metadata + learnings por peça (artigo ou post) |
| `series/<nome-da-serie>.md` | Séries com arco narrativo e ordem de publicação |

## Frontmatter de artigo/post

```yaml
---
tags: [content, article | post, <tema>]
status: rascunho | revisao | publicado
created: YYYY-MM-DD
published: YYYY-MM-DD
canal: linkedin | x | blog
serie: <nome-da-serie>           # opcional
relacionado: [[slug-do-par]]      # liga artigo ao post (e vice-versa)
---
```

## Convenções

- Texto completo do artigo pode viver fora do vault (ex.: Notion); aqui só metadata + learnings
- Séries têm cadência declarada e `/daily-briefing` sugere próxima publicação
- `persona.md` / `themes.md` / `ideas-backlog.md` começam ausentes — criar antes de usar pipeline editorial
- Diretório nasce vazio; popula com o uso
