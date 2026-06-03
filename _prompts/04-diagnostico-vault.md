# 04 — Diagnóstico Adaptativo do Knowledge Graph

Use este prompt para verificar a saúde do vault. O diagnóstico é **adaptativo**: reporta sobre o que existir, sem cobrar números hardcoded. Cole no Claude Code dentro do diretório `$VAULT`.

---

Faça um diagnóstico do knowledge graph em `$VAULT`. Verifique cada componente e produza um relatório de saúde proporcional ao que existe.

## 1. Camada 0 — Navegação (`_index/`)

Para cada arquivo presente em `_index/`:
- [ ] Existe e tem conteúdo real (não só cabeçalhos)?
- [ ] Os links WikiLinks apontam para arquivos que existem?

Arquivos esperados (criar se faltar e tiver demanda):
`MASTER-INDEX.md`, `PATTERN-MATRIX.md`, `FEATURE-CATALOG.md`, `CONCEPT-INDEX.md`, `TAG-TAXONOMY.md`, `OBSIDIAN-GRAPH-VIEWS.md`

Reporte: `X/N índices presentes`, onde N é o número que faz sentido para o seu vault. Vault vazio é OK se você ainda não populou padrões/features.

## 2. Camada 2A — Padrões (`_patterns/`)

Conte arquivos `*.md` (exceto README.md). Para cada padrão:
- [ ] Tem seção `## What It Solves`?
- [ ] Tem seção `## How It Works Here` com regras específicas?
- [ ] Tem seção `## Projects Using This Pattern` com pelo menos 1 linha?
- [ ] Tem seção `## When NOT to Use`?
- [ ] Tem seção `## Related Patterns` com WikiLinks?

Reporte: `X padrões documentados; Y completos; Z incompletos (com listagem)`.

## 3. Camada 2B — Features (`_features/`)

Conte arquivos `*.md` (exceto README.md). Para cada feature:
- [ ] Frontmatter tem `status` (`production`, `poc`, ou `planned`)?
- [ ] Frontmatter tem `pattern:` com link para `_patterns/`?
- [ ] Tem seção `## Implementation Location` com paths reais?
- [ ] Tem seção `## How to Reuse` com passos numerados?

Reporte: `X features; Y production; Z poc; W planned; K incompletas`.

## 4. Camada 1 — Projetos (`_knowledge/projects/`)

Excluir pasta `_template/` da contagem. Para cada projeto restante:
- [ ] Tem `<projeto>.md` (índice) com menos de 50 linhas?
- [ ] Tem `modules.md`?
- [ ] Tem `gotchas.md` com ao menos 1 item?
- [ ] Tem `state.md` com estado atual?
- [ ] `<projeto>.md` linka para pelo menos 1 padrão ou feature (se houver)?

Reporte: `X projetos; Y com estrutura completa; Z com lacunas`.

## 5. Integridade do Grafo

- [ ] Existem broken links (WikiLinks apontando para arquivos inexistentes)?
- [ ] Cada feature linka de volta para seu pattern parent?
- [ ] PATTERN-MATRIX (se existir) cobre todos os patterns nas colunas?
- [ ] FEATURE-CATALOG (se existir) lista todas as features com paths corretos?

Use `.claude/scripts/graph-metrics.sh` se quiser métricas detalhadas (broken links, ilhas, hubs).

## 6. AGENTS.md — Contrato Agentico

- [ ] Seção 2 (Identidade) está preenchida (sem `<preencher>`)?
- [ ] Seção 3 (Regras de memória) descreve protocolo coerente com o estado real do vault?
- [ ] Mapa de Workflows reflete os comandos efetivamente presentes em `.claude/commands/`?

## 7. Slash Commands

- [ ] Cada `.claude/commands/<cmd>.md` tem skill paritária em `.codex/skills/sb-<cmd>/SKILL.md`?
- [ ] Rode `bash tests/test-codex-parity.sh` — sai zero?
- [ ] Algum command referencia diretório inexistente?

## 8. Memória e Runtime

- [ ] `_memory/current-state.md` existe se houve sessão produtiva recente?
- [ ] `_memory/activity-log.md` tem entradas dos últimos 7 dias?
- [ ] Há flags pendentes (`.needs-end-session`, `.compacted-without-end-session`)?

## 9. Lint e Segurança

- [ ] `bash .claude/scripts/lint-pre-donate.sh .` retorna apenas falsos positivos (lint + fixture)?
- [ ] `bash tests/test-secret-guard.sh` passa?

---

## Output Esperado

```
### Diagnóstico do Knowledge Graph — {data}

**Nota geral:** [X/10] proporcional ao que foi populado

| Componente | Status | Observação |
|------------|--------|------------|
| Camada 0 (Índices) | [X/N] | [quais existem e quais faltam] |
| Padrões (_patterns/) | [X documentados] | [completos vs incompletos] |
| Features (_features/) | [X] | [breakdown por status] |
| Projetos (_knowledge/projects/) | [X projetos] | [com estrutura completa vs lacunas] |
| Grafo (links) | [OK / N broken links] | [listar broken links] |
| AGENTS.md | [Identidade preenchida? Workflows alinhados?] | |
| Paridade Codex | [OK / discrepâncias] | |
| Memória runtime | [recente / desatualizada] | |
| Lint anti-IP | [verde / violações reais] | |

**Bloqueadores críticos:**
[Lista priorizada, somente o que impede uso normal]

**Próximo passo recomendado:**
[A ação mais valiosa agora — proporcional ao estado do vault]
```

---

## Regras

- **Não exigir contagens mínimas** — vault vazio é estado válido para scaffold recém-clonado
- Reportar lacunas como observação, não como falha, exceto quando algo claramente quebrado (broken links, paridade fora)
- Priorizar: o que impede uso normal vs. o que é só "ainda não populado"
- Não inventar conteúdo — se o vault está vazio, o relatório é curto e diz isso
