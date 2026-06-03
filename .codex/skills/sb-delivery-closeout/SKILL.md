---
name: sb-delivery-closeout
description: "Feche uma entrega com validacoes, git status, PR/merge/tag quando autorizado, docs, capturas assistidas e end-session."
license: Apache-2.0
metadata:
  owner: second-brain
  vault: "$VAULT"
  vault_name: "Second Brain"
  vault_prefix: "sb"
  source_command: ".claude/commands/delivery-closeout.md"
---

# Second Brain Delivery Closeout

Use ao final de implementacao, wave, PR ou release candidate.

## Workflow

1. Confirme escopo e gaps como em `sb-completion-audit`.
2. Verifique `git status --short` e separe mudancas do escopo de mudancas pre-existentes.
3. Rode validacao `quick`, `full` ou `live` conforme risco.
4. Prepare commit/PR/merge/tag apenas quando autorizado ou permitido pela politica do projeto.
5. Se houver PR, merge, tag ou release, garanta captura assistida em `_pipeline/inbox/`.
6. Atualize docs operacionais quando comportamento ou workflow mudou.
7. Encerre com `sb-end-session` ou script equivalente.
8. Declare no final `vault: atualizado`, `vault: pendente` ou `vault: nao aplicavel`.

## Regras

- Nao reverta mudancas que nao foram feitas nesta entrega.
- Nao escreva secrets em logs, markdown, prompts ou regras.
- Nao promova captura assistida para nota permanente sem revisao humana.
- Nao declare fechamento com teste obrigatorio falhando sem aceite explicito.
- Toda resposta final deste fluxo deve declarar `vault: atualizado`, `vault: pendente` ou `vault: nao aplicavel`.
