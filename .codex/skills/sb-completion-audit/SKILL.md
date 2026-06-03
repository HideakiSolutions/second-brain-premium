---
name: sb-completion-audit
description: "Audite completude de uma entrega comparando proposta, docs, codigo, testes e ambiente real; gere percentual funcional, gaps e plano."
license: Apache-2.0
metadata:
  owner: second-brain
  vault: "$VAULT"
  vault_name: "Second Brain"
  vault_prefix: "sb"
  source_command: ".claude/commands/completion-audit.md"
---

# Second Brain Completion Audit

Use quando uma proposta, PR, branch, wave ou entrega precisa de verificacao objetiva antes de ser considerada pronta.

## Workflow

1. Identifique o escopo declarado na proposta, docs, issue, plano, PR ou conversa.
2. Leia arquivos alterados e documentacao minima relevante.
3. Compare comportamento prometido contra codigo, testes e configuracao real.
4. Rode validacoes proporcionais ao risco.
5. Cheque ambiente real quando houver servico, deploy, fila, banco, URL ou GitOps.
6. Responda com `% funcional`, evidencias, gaps, validacoes e plano para 100%.

## Regras

- Nao aceite "feito" sem evidencia ou limitacao explicita.
- Nao mascare scaffold como produto funcional.
- Nao copie prompts brutos do log efemero.
- Se faltar acesso externo, registre como gap.
- Nao faca merge, tag ou escrita duravel no vault.
