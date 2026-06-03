---
description: Audita frontmatter contra TAG-TAXONOMY.md, lista violações, sugere correções
allowed-tools: Bash(.claude/scripts/graph-metrics.sh), Read(_memory/graph-metrics.md), Read(_index/TAG-TAXONOMY.md), Read
---

# /tag-audit

Audita o frontmatter de todos os .md do vault contra `_index/TAG-TAXONOMY.md`.

## Execução

1. Rodar `bash .claude/scripts/graph-metrics.sh` para capturar a lista atual de tags fora da taxonomia
2. Ler `_memory/graph-metrics.md`, seção "Tags fora da taxonomia"
3. Para cada arquivo violador:
   - Ler frontmatter atual
   - Cruzar com a taxonomia (`_index/TAG-TAXONOMY.md`)
   - Sugerir correção (camada inferida do diretório, domínio inferido do conteúdo)
4. Se o usuário confirmar, aplicar correções via Edit nos frontmatters
5. Re-rodar `graph-metrics.sh` ao final para validar

## Heurísticas de correção

- Arquivo em `_patterns/` → camada `pattern` + maturidade `active`
- Arquivo em `_features/` → camada `feature` + maturidade `production` (default)
- Arquivo em `_decisions/` → camada `decision` + maturidade `active`
- Arquivo em `_learnings/` → camada `learning` + maturidade `active`
- Arquivo em `_knowledge/projects/<X>/` → camada `project` + tag estrutural baseada no nome (`work-log` para work-log.md, etc.)
- Arquivo em `_cores/` → camada `core` + maturidade do front-matter ou `candidate`
- Arquivo em `_index/` → camada `index` + maturidade `active`

## Quando usar

- Após criar TAG-TAXONOMY pela primeira vez (bootstrap)
- Após adicionar nova categoria à taxonomia
- Periodicamente para detectar drift

## Saída

Tabela:

| Arquivo | Violações | Correção sugerida |
|---|---|---|
| `_decisions/X.md` | tags `[arquitetura]` (não existe) | mudar para `[architecture, governance]` |
