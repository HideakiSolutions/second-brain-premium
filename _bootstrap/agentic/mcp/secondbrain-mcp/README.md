# secondbrain-mcp

MCP server que expõe o second brain (recall associativo + grafo FalkorDB) como tools para qualquer sessão Claude Code, em qualquer projeto.

A raiz do vault é resolvida automaticamente pela posição deste pacote; para vaults fora do padrão, defina `SECONDBRAIN_VAULT=/caminho/do/vault`.

## Pré-requisitos

1. FalkorDB rodando localmente (sobe junto com a stack):
   ```bash
   bash _bootstrap/agentic/stack.sh start
   ```

2. Grafo sináptico construído:
   ```bash
   bash .claude/scripts/sb-synapse.sh build
   ```

3. Dependências Node instaladas:
   ```bash
   cd _bootstrap/agentic/mcp/secondbrain-mcp
   npm install --omit=dev
   ```

## Registrar no Claude Code

```bash
claude mcp add secondbrain-mcp \
  node <VAULT>/_bootstrap/agentic/mcp/secondbrain-mcp/src/index.js
```

Ou manualmente em `~/.claude.json`, seção `mcpServers`:

```json
{
  "mcpServers": {
    "secondbrain-mcp": {
      "command": "node",
      "args": ["<VAULT>/_bootstrap/agentic/mcp/secondbrain-mcp/src/index.js"]
    }
  }
}
```

## Tools disponíveis

| Tool | Descrição |
|------|-----------|
| `recall` | **Recall associativo**: sementes semânticas (Qdrant) + spreading activation sobre sinapses com peso + força de uso. Resultados carregam a cadeia de memórias. Modo `seed` expande a partir de uma nota (offline). |
| `memory_chain` | Caminho sináptico mais forte entre duas notas (como duas memórias se conectam) |
| `reinforce` | Reforço hebbiano das memórias co-ativadas numa janela/sessão |
| `query_graph` | Cypher arbitrário contra o FalkorDB |
| `multi_hop` | Travessia a partir de uma entidade até profundidade N |
| `entity_neighbors` | Vizinhos diretos de uma entidade |
| `why_decision` | Referências + projetos afetados de um ADR |
| `find_similar_decisions` | Semântico (recall sobre decisões) com fallback keyword quando a stack está offline |
| `get_project_state` | Info do grafo + state.md cru de um projeto |
| `graph_stats` | Contagens de entidades/relações |

## Graph `synapse` (projeção do grafo sináptico)

- **Nodes:** `(:Note {id, slug, kind, project, title, importance})` — todas as notas do vault
- **Edges:** WIKILINK, RELATED, SUPERSEDES, STRUCTURAL, TAG_SIBLING, LEARNED — todas com `weight` (0..1) e `source` (`file`|`learned`)
- Projeção **near-online**: sync incremental automático após build/reinforce/decay; reconciliação full no `/consolidate` semanal
- Estado canônico das sinapses: SQLite `_memory/.synapse/synapse.db` (ver `_bootstrap/agentic/synapse/README.md`)

## Exemplos (Cypher)

```cypher
-- vizinhança ponderada de uma nota
MATCH (n:Note {slug:'idempotency'})-[r]-(m) RETURN m.id, type(r), r.weight ORDER BY r.weight DESC LIMIT 15

-- sinapses aprendidas por uso (candidatas a WikiLink real)
MATCH ()-[r {source:'learned'}]->() RETURN r.weight ORDER BY r.weight DESC LIMIT 10
```
