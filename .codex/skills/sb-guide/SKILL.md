---
name: sb-guide
description: "Carrega o mapa autoritativo do second-brain (skill second-brain-guide) e responde sobre arquitetura, comandos, fluxos ou onde está algo."
license: Apache-2.0
metadata:
  owner: second-brain
  vault: "$VAULT"
  vault_name: "Second Brain"
  vault_prefix: "sb"
  source_command: ".claude/commands/guide.md"
---

# Second Brain Sb Guide

This is the Codex port of `sb-guide` from `.claude/commands/sb-guide.md`.

When the original command mentions `$ARGUMENTS`, treat it as the current user input or the text following the skill invocation.

Use `$VAULT` as the vault root for all relative paths unless the user provides another path.


# /sb-guide

Carrega a skill `second-brain-guide` (em `~/.claude/skills/second-brain-guide/`) e usa o mapa para responder sobre o vault.

## Argumentos

`$ARGUMENTS` é a pergunta do usuário. Pode ser:
- Estrutural: "como funciona o auto-linker?", "onde fica o curator?", "lista os comandos"
- Roteamento: "como pergunto sobre decisões?", "que skill usa pra style?"
- Workflow: "como adiciono um projeto?", "como crio um novo padrão?"

## Execução

1. **Invoque a skill** via Skill tool: `Skill(skill: "second-brain-guide")`
2. Use o mapa carregado para responder. Se a pergunta for sobre CONTEÚDO (decisões, learnings, projetos), encaminhe para `/ask` ou `/sb-search` em vez de tentar responder direto.
3. Sempre cite paths absolutos quando referenciar arquivos.
4. Se não souber, diga e sugira `/sb-search` para descobrir.

## Output

Resposta estruturada em PT-BR com:
- Resposta direta (se estrutural)
- OU encaminhamento para a ferramenta certa (se de conteúdo)
- Paths absolutos verificáveis quando aplicável
- Nunca alucinar comandos ou diretórios — só usar o que a skill documenta
