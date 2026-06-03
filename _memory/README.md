# `_memory/` — Runtime State

Estado operacional do vault. **Conteúdo gerado por hooks e comandos** — não editar manualmente.

## O que vive aqui

| Arquivo | Origem | Função |
|---|---|---|
| `current-state.md` | `/end-session` | Snapshot do contexto atual da sessão (work-in-progress, próximos passos, bloqueios) |
| `activity-log.md` | hooks `SessionEnd` + comandos | Log append-only de operações (formato `## [YYYY-MM-DD HH:MM] op \| descricao`); retenção 90 dias |
| `heartbeat-latest.md` | cron `daily-heartbeat` | Resultado do último health-check automático |
| `lint-latest.md` | cron `weekly-vault-lint` | Resultado do último lint completo |
| `graph-metrics.md` | `/graph-metrics` | Métricas do grafo (links, ilhas, hubs) |
| `.needs-end-session` | hook `SessionEnd` | Flag: sessão encerrada sem `/end-session` |
| `.compacted-without-end-session` | hook `PreCompact` | Flag: compactação ocorreu sem `/end-session` |
| `.pre-compact-notes.md` | hook `PreCompact` | Snapshot crítico antes da compactação |
| `.prompt-log.txt` | hook `UserPromptSubmit` | Log efêmero de prompts (sanitizado, agregado) |

## Convenções

- Nunca commitar flags `.needs-*`, `.compacted-*`, `.prompt-log.txt` — estão no `.gitignore`
- `activity-log.md` é append-only; entradas antigas migram para `_sessions/`
- `current-state.md` é sobrescrito a cada `/end-session`
- Diretório nasce vazio no scaffold; popula com o uso
