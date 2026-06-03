# `_pipeline/` — Planejamento e Inbox

Itens ativos de planejamento, RFCs e captura automatizada (inbox).

## Estrutura

| Caminho | Função |
|---|---|
| `inbox/auto-captures-YYYY-MM-DD.md` | Eventos auto-capturados por hooks (revisar via `/review-captures`) |
| `<slug>.md` | RFCs, design docs, planos de entrega (criar via `/rfc <tema>`) |
| `dev-squad-runs/<run-id>/` | Runs do `/dev-squad` (planejamento Opus + execução paralela Sonnet/Haiku) |
| `self-improvement-candidates.md` | Output do `/learn-loop` — candidatos a evolução de skills/commands/hooks |
| `curation-proposals.md` | Output do `/curate-vault` — propostas de organização |

## Convenções

- Inbox é volátil — após `/review-captures` ou consolidação no `/end-session`, itens promovidos viram nota canônica em `_learnings/`, `_decisions/`, `_sessions/` ou são descartados
- RFCs têm frontmatter com `status: proposed | accepted | superseded | rejected`
- Diretório nasce vazio; popula com o uso
