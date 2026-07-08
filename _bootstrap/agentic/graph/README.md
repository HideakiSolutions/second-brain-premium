# `graph/` — Cliente FalkorDB

Cliente mínimo para o FalkorDB (protocolo Redis, `GRAPH.QUERY`/`GRAPH.DELETE`), usado pela camada sináptica para projetar o grafo nota-a-nota com pesos no graph `synapse` (consultável via Cypher e pelo `secondbrain-mcp`).

- `falkor_client.py` — usa `redis-py` quando disponível; fallback RESP2 por raw socket (stdlib-only). Fail-soft: métodos retornam `None`/lista vazia com FalkorDB offline.
- Config default: `127.0.0.1:6379`.

O FalkorDB é **opcional**: sem ele, o recall associativo continua funcionando (o estado canônico das sinapses é o SQLite da camada `synapse/`); apenas a superfície Cypher fica indisponível.
