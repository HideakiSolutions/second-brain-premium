---
name: sb-ux-product-audit
description: "Audite frontend como produto real vs MVP incompleto vs scaffold, com gaps UX, tecnicos e testes ausentes."
license: Apache-2.0
metadata:
  owner: second-brain
  vault: "$VAULT"
  vault_name: "Second Brain"
  vault_prefix: "sb"
  source_command: ".claude/commands/ux-product-audit.md"
---

# Second Brain UX Product Audit

Use para avaliar frontend, admin, dashboard, landing, PWA ou fluxo visual antes de declarar pronto para usuario.

## Workflow

1. Identifique persona e fluxo principal.
2. Rode ou inspecione app em desktop e mobile quando possivel.
3. Verifique navegacao, vazio, loading, erro, auth, responsividade e dados reais vs mock.
4. Rode Playwright/screenshot/axe quando disponivel e proporcional.
5. Classifique como `produto real`, `MVP incompleto` ou `scaffold`.
6. Priorize gaps por impacto no usuario.

## Regras

- Nao confunda layout bonito com produto pronto.
- Nao aceite mock quando a operacao exige dados reais.
- Verifique texto, overflow e responsividade.
- Se nao conseguir executar, declare limitacao e audite por codigo com menor confianca.
