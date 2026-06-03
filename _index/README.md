# `_index/` — Catálogos Navegáveis

Camada 0 do knowledge graph: mapas e índices regeneráveis a partir de `_patterns/`, `_features/`, `_knowledge/projects/`, `_decisions/`.

## Arquivos esperados

| Arquivo | Função | Gerado por |
|---|---|---|
| `MASTER-INDEX.md` | Mapa do vault em <80 linhas (projetos, padrões, features, próximas ações) | manual + `/lint` |
| `PATTERN-MATRIX.md` | Tabela padrão × projeto (quem usa o quê) | `.claude/scripts/pattern-matrix-generator.sh` |
| `FEATURE-CATALOG.md` | Catálogo de features reutilizáveis com status (production/poc/planned) | `.claude/scripts/concept-extractor.sh` |
| `CONCEPT-INDEX.md` | Conceitos transversais e onde aparecem | `.claude/scripts/concept-extractor.sh` |
| `TAG-TAXONOMY.md` | Tags válidas + quando usar cada uma | manual + `/tag-audit` |
| `OBSIDIAN-GRAPH-VIEWS.md` | Configurações sugeridas de graph view no Obsidian | manual |

## Uso

- `MASTER-INDEX.md` deve ser lido em todo início de sessão
- Comandos como `/focus`, `/daily-briefing`, `/justify` consultam estes índices
- Regenerar após mudanças estruturais grandes: `bash .claude/scripts/pattern-matrix-generator.sh`

## Convenções

- Índices são curtos e navegacionais — não duplicam conteúdo
- WikiLinks `[[../_patterns/saga-pattern]]` apontam para fonte
- Diretório nasce vazio; popula quando você criar seu primeiro pattern/feature/projeto
