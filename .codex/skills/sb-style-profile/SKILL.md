---
name: sb-style-profile
description: "Regenera o style fingerprint empírico a partir dos artigos publicados em _content/articles/."
license: Apache-2.0
metadata:
  owner: second-brain
  vault: "$VAULT"
  vault_name: "Second Brain"
  vault_prefix: "sb"
  source_command: ".claude/commands/style-profile.md"
---

# Second Brain Style Profile

This is the Codex port of `style-profile` from `.claude/commands/style-profile.md`.

When the original command mentions `$ARGUMENTS`, treat it as the current user input or the text following the skill invocation.

Use `$VAULT` as the vault root for all relative paths unless the user provides another path.


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
