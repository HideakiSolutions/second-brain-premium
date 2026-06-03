---
description: Regenera o style fingerprint empírico a partir dos artigos publicados em _content/articles/.
allowed-tools: Bash(.claude/scripts/style-profile.sh:*), Read(_bootstrap/agentic/style/fingerprint.json)
---

# /style-profile

Reanálise dos artigos publicados em `_content/articles/*.md` para regerar o fingerprint estatístico da voz autoral.

## Quando usar

- Após publicar 3+ artigos novos (deslocam médias do fingerprint)
- Após editar substancialmente artigos antigos
- Bootstrap inicial pós-Onda 5

## Execução

```bash
bash .claude/scripts/style-profile.sh
```

Saída: regrava `_bootstrap/agentic/style/fingerprint.json`. Imprime resumo: número de artigos analisados, médias-chave (parágrafos, palavras, tropos).

## Resultado

Mostre ao usuário:
- Número de artigos no corpus
- Estatística-chave: word_count.mean, em_dash.mean, tropes.contraste_nao_e.rate, closing_question.rate
- Caminho do JSON gerado
