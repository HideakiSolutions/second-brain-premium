# `_infrastructure/` — Estado Operacional de Infra

Snapshots e contexto estático do seu ambiente operacional (clusters K8s, ambientes, ferramentas, secrets-map). Útil quando você opera infra compartilhada e quer rastrear mudanças.

## Estrutura sugerida

| Caminho | Função |
|---|---|
| `SNAPSHOT.md` | Estado atual do cluster (auto-gerado por `infra-snapshot.sh`) |
| `environments/<env>.md` | Contexto de cada ambiente (dev, staging, prod, máquinas locais) |
| `k8s/` | Manifests de referência, observabilidade, networking |
| `tools/<tool>.md` | Ferramentas instaladas e configuração |
| `secrets/secrets-map.md` | Mapa de secrets por ambiente (sem valores — apenas refs ao vault de secrets) |
| `gitops/` | Configurações GitOps (ArgoCD, Flux) |
| `repo-map.yaml` | Mapa repo→ambiente |
| `argocd-mapping.yaml` | Mapa app→cluster |
| `capture-modes.yaml` | Configuração do `event-router.sh` |
| `event-filters.yaml` | Filtros de eventos auto-capturados |

## Origem

- Manual: criar arquivos conforme infra evolui
- Hook `on-session-end`: dispara `infra-snapshot.sh` automaticamente quando sessão tocou infra (detectado via grep no transcript por `kubectl|argocd|namespace|deploy|k8s`)
- `/end-session` (passo 6.5): registra mudanças de infra detectadas

## Convenções

- **Nunca commitar valores de secrets** — apenas nomes/refs (`secrets-map.md` aponta para o vault de secrets real)
- Diretório nasce vazio; popula com o uso quando você operar infra compartilhada
