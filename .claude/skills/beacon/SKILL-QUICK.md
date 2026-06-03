---
name: beacon
tier: quick
version: "1.1"
description: "Quick beacon: cruza vault + projeto (CWD) e aponta a próxima ação. GATE de projeto bloqueante, ordena por urgência, recomenda UMA ação. Tier 1 — leitura mínima. NUNCA cruza outros projetos."
trigger: "próximas atividades, o que fazer agora, qual a próxima coisa, next up, what next, status do projeto, backlog ativo, agenda do projeto"
skip: "debugando erro específico; tarefa explícita em curso; próxima ação óbvia; pediu portfólio puro (/pipeline); pediu state puro (/focus)"
license: Apache-2.0
metadata:
  canonical_source: "second-brain/.claude/skills/beacon/SKILL-QUICK.md (origem versionada). Cópia em ~/.claude/skills/beacon/."
---

# Beacon — Quick Protocol (Tier 1)

Farol de próxima ação. Cruza vault + repo da CWD, classifica por urgência, recomenda UMA coisa.
**Estritamente project-scoped** (ver SKILL.md tier 2 para o protocolo completo e o porquê).

## Step 0 — GATE: detectar e validar projeto (BLOQUEANTE)

```bash
VAULT=$VAULT
PROJECT="${ARGUMENTS:-$(basename "$PWD")}"
[ -d "$VAULT/_knowledge/projects/$PROJECT" ] || PROJECT=""
# fallback: CLAUDE.md (Repository: / # CLAUDE.md — <nome>), revalidar contra _knowledge/projects/
```

- Projeto resolvido e registrado → seguir.
- CWD com sinais mas não registrado → operar só com repo; sugerir `/end-session`.
- Nenhum projeto → **degradar para `/pipeline`** e dizer isso. **Não** ler fontes do vault como projeto.

## Step 1 — Ler fontes (cap 12 arquivos) — SOMENTE do projeto resolvido

| Fonte | Limite |
|---|---|
| `_knowledge/projects/{p}/TASKS.md` | inteiro, se existir (preferida) |
| `_knowledge/projects/{p}/state.md` | inteiro |
| `_knowledge/projects/{p}/roadmap.md` | fase atual |
| `_knowledge/projects/{p}/work-log.md` | 3 últimas |
| `_pipeline/*.md` com `project: {p}` no frontmatter | match EXATO (sem campo → ignora) |
| STATE.md / docs canonical (repo) | se houver |

**PROIBIDO:** `_memory/current-state.md` (rollup cross-project), `_knowledge/projects.md` inteiro,
`_pipeline/` por menção textual, qualquer outro projeto.

## Step 2 — Output (PT-BR)

```markdown
# Beacon — {projeto} — {data}
## Escopo: {projeto} (fonte: {arg|CWD|CLAUDE.md})
## Bloqueadores
## Em andamento (branch, PRs)
## Próximas (priorizadas)
## Recomendação única
```

## Regras
- PT-BR, direto. UMA recomendação mandatória.
- **Project-scope inviolável** — nunca item de outro projeto.
- Read-only. Nunca commita.
- Sem projeto → `/pipeline` filtrado (explícito).
