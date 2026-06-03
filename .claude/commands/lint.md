Você é o auditor do knowledge graph. Verifique a saúde do vault e produza um relatório de defeitos.

## Argumentos opcionais

- (sem argumento): auditoria completa, somente leitura
- `--fix`: aplica `auto-linker.sh --apply` + `concept-extractor.sh` + `pattern-matrix-generator.sh` antes de auditar (densifica grafo automaticamente quando seguro)
- `--graph`: focar apenas nas métricas do grafo (ilhas, hubs, broken, tags). Equivalente a `/graph-metrics`.
- `--check-templates`: verifica apenas se arquivos críticos de projeto têm seções `## Padrões Aplicados` / `## Features Reutilizadas` / `## Decisões Relacionadas`

## Passos

Execute todas as verificações abaixo. Para cada uma, conte defeitos e liste os itens com problema.

### 1. Sincronismo de Índices (impacto: crítico)

Se existir `_index/MASTER-INDEX.md`:
- Para cada projeto listado, verificar se existe pasta em `_knowledge/projects/{nome}/`
- Para cada pasta existente, verificar se está listada no MASTER-INDEX
- Defeito: pasta sem entrada no índice, ou entrada sem pasta

Se existir `_index/PATTERN-MATRIX.md`:
- Para cada padrão listado, verificar se existe arquivo em `_patterns/{nome}.md`

Se existir `_index/FEATURE-CATALOG.md`:
- Para cada feature listada, verificar se existe arquivo em `_features/{slug}.md`

### 2. Frontmatter Obrigatório (impacto: alto)

Verificar todos os arquivos em:
- `_patterns/*.md` (se existir)
- `_features/*.md` (se existir)
- `_knowledge/projects/*/*.md` (se existir)

Campos obrigatórios: `tags`, `status`, `created`
Defeito: arquivo sem um ou mais desses campos
Pular arquivos `_exemplo.md` — são templates de referência.

### 3. Notas Obsoletas (impacto: médio)

Verificar arquivos com `status: active` que têm `updated` com data > 30 dias atrás.
Sinalizar como candidatos a revisão.

### 4. WikiLinks Quebrados (impacto: alto)

Nos arquivos de `_patterns/`, `_features/`, e projetos:
- Extrair todos os padrões `[[...]]` e `[[...|...]]`
- Para cada link, verificar se o arquivo-alvo existe no vault
- Defeito: link para arquivo inexistente

### 5. Arquivos Órfãos (impacto: baixo)

Verificar arquivos em `_features/` e `_patterns/` que não são referenciados por nenhum outro arquivo.
Candidatos a remoção ou documentação adicional.

### 6. Taxonomia de tags (impacto: alto)

Comparar tags do frontmatter contra `_index/TAG-TAXONOMY.md`:
- Camada (1 obrigatória): pattern, feature, decision, learning, project, core, infra, content, source, index, memory, session, wiki
- Maturidade (1 obrigatória): production, beta, mvp, spike, candidate, deprecated, archived, active, wip
- Domínio (≥1 obrigatório em projetos)

Defeito: tag fora da taxonomia, camada ausente/duplicada, maturidade ausente/duplicada.

Reuso: o script `bash .claude/scripts/graph-metrics.sh` calcula isso automaticamente e grava em `_memory/graph-metrics.md`.

### 7. Densidade do grafo (impacto: alto)

Rodar `bash .claude/scripts/graph-metrics.sh` e ler `_memory/graph-metrics.md`. Reportar:
- % ilhas total e por categoria
- Cobertura projetos×patterns (alvo: ≥90% com ≥3 patterns linkados)
- Patterns/features sem backlinks (alvo: 0)

Targets-alvo a 30 dias:
- Ilhas ≤ 15%
- Grau médio ≥ 8
- Tags fora taxonomia: 0
- Broken links: 0

### 8. Templates obrigatórios (apenas com `--check-templates` ou em modo completo)

Para cada `_knowledge/projects/<projeto>/{state,decisions,gotchas,modules,index}.md`:
- Seção `## Padrões Aplicados` presente (mínimo 2 links para `_patterns/`)
- Em `<projeto>.md` e `modules.md`: também `## Features Reutilizadas` (mínimo 1)
- Em `decisions.md` e `gotchas.md`: também `## Decisões Relacionadas` (mínimo 1)

Progressive disclosure:
- `decisions.md` e `gotchas.md` são manifestos; devem conter `## Como usar`, `## Entradas Ativas e Recentes` e `## Arquivo Completo`.
- Validar frontmatter em `_knowledge/projects/<projeto>/decisions/*.md` e `_knowledge/projects/<projeto>/gotchas/*.md`.
- Cada arquivo detalhado deve linkar de volta para `[[../<projeto>|<projeto>]]` e para o manifesto `[[../decisions|decisions.md]]` ou `[[../gotchas|gotchas.md]]`.
- Defeito: entrada detalhada sem link no manifesto correspondente.

### 9. Registrar no activity log

Append em `_memory/activity-log.md`:
```
## [YYYY-MM-DD HH:MM] lint | [N] defeitos críticos, [N] avisos
```

## Output

Responda **em português (BR)** com:

### Relatório de Lint — [data de hoje]

**Nota geral:** [X/10]

| Verificação | Defeitos | Avisos | Status |
|-------------|---------|--------|--------|
| Sincronismo de índices | [N] | [N] | [OK / FALHOU] |
| Frontmatter obrigatório | [N] | — | [OK / FALHOU] |
| Notas obsoletas | — | [N] | [OK / ATENÇÃO] |
| WikiLinks quebrados | [N] | — | [OK / FALHOU] |
| Arquivos órfãos | — | [N] | [OK / ATENÇÃO] |

**Defeitos Críticos** (corrigir antes da próxima sessão):
[Lista numerada com arquivo + problema + ação para corrigir]

**Avisos** (corrigir quando possível):
[Lista com arquivo + situação]

**Ações prioritizadas:**
1. [Ação mais impactante]
2. [Segunda ação]
3. [...]

## Regras

- Não reportar como OK sem verificar o conteúdo real dos arquivos
- Registrar no activity log independente do resultado (mesmo se zero defeitos)
- Ser objetivo — listas, não parágrafos
- Pular arquivos `_exemplo.md` em todas as verificações
