---
name: sb-live-deploy-validate
description: "Valide deploy live em GitOps/k3s/ArgoCD, imagem, rollout, health, URL publica e smoke."
license: Apache-2.0
metadata:
  owner: second-brain
  vault: "$VAULT"
  vault_name: "Second Brain"
  vault_prefix: "sb"
  source_command: ".claude/commands/live-deploy-validate.md"
---

# Second Brain Live Deploy Validate

Use quando uma entrega depende de Kubernetes, k3s, ArgoCD, GitOps, ingress, imagem container, DNS ou URL publica.

## Workflow

1. Identifique app, namespace, ambiente, imagem esperada e URL publica.
2. Verifique manifests/GitOps e revisao esperada.
3. Cheque ArgoCD sync/health quando disponivel.
4. Cheque Kubernetes: namespace, rollout, pods, restarts, service e ingress.
5. Confirme imagem real contra a esperada.
6. Execute smoke HTTP ou comando especifico.
7. Liste gaps de acesso, credencial, namespace ou ambiente.

## Regras

- Nao crie ou altere secrets.
- Nao aplique manifests manualmente sem autorizacao explicita.
- Nao trate synced como suficiente sem health/smoke quando houver URL ou API.
- Se ambiente nao estiver acessivel, classifique como nao validado.
