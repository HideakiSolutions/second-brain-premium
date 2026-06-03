# `_cores/` — Core Repos Compartilhados (opcional)

Camada 1B do knowledge graph: bibliotecas/módulos compartilhados entre múltiplos projetos do seu portfólio. **Opcional** — só faz sentido se você mantém core repos transversais (auth, design-system, messaging, etc.).

## Quando usar

Você tem um repositório separado (ou submódulo) que vários projetos consomem. Quer documentar:
- O que o core oferece
- Quem consome
- Gaps e candidatos a promoção (código duplicado em projetos que poderia subir pro core)

## Arquivos sugeridos

| Arquivo | Função |
|---|---|
| `<core-name>.md` | Manifesto do core: ofertas, consumidores, gaps |
| `promotion-backlog.md` | Fila de candidatos a promoção (vindo de `_pipeline/` ou `/end-session`) |
| `weekly-report-latest.md` | Output do cron `weekly-core-session` |

## Origem

- Manual: criar `<core>.md` quando começa um core compartilhado
- Cron `weekly-core-session` gera relatório semanal de drift
- `/core-session [projeto | new]` analisa core drift e gera checklist

## Convenções

- Se você não mantém cores compartilhados, deixe este diretório vazio — comandos `/core-session` reportam "sem cores ativos"
- Diretório nasce vazio; popula com o uso
