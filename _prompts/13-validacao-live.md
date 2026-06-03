# Validacao Live

Use para deploys em GitOps/k3s/ArgoCD.

## Prompt

Valide app, namespace, revisao GitOps, imagem esperada, rollout, pods, services, ingress, health, URL publica e smoke. Se nao houver acesso ao cluster ou URL, classifique como nao validado e liste o comando exato que falta executar.

## Regras

- Sync nao basta sem health/smoke quando ha API ou UI publica.
- Nao criar ou alterar secrets.
- Nao aplicar manifests manualmente sem autorizacao explicita.
