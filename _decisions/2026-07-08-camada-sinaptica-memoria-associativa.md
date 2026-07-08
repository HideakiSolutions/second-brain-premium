---
tags: [decision, knowledge-mgmt, ai-sdlc, architecture]
status: active
created: 2026-07-08
updated: 2026-07-08
---

# ADR - Camada Sináptica: Memória Associativa para o Second Brain

**Aplicação:** o vault + qualquer agente (Claude Code, Codex, runtimes equivalentes) que o consuma como suporte à decisão. Este ADR documenta a arquitetura da capacidade que acompanha o scaffold - e serve de exemplo do formato de decisão.

## Contexto

Um vault estruturalmente saudável (links íntegros, frontmatter taxonômico, busca semântica) ainda pode ser cognitivamente **estático**:

1. **Camadas desconectadas.** Busca vetorial (Qdrant) e grafo de links são silos: a busca não navega o grafo, e o grafo não conhece similaridade.
2. **Sinapses sem fisiologia.** Links não têm tipo semântico rico nem peso, não fortalecem com uso, não enfraquecem com desuso. Um link criado há meses vale o mesmo que um usado ontem 50 vezes.
3. **Nenhum sinal de uso aproveitado.** Buscas, leituras e recalls não deixam rastro estruturado - não existe o loop "recuperei junto, então conecta" nem "nunca mais usei, então esquece gradualmente".
4. **Memória de trabalho cresce sem consolidação.** O rollup "recente" (`_memory/current-state.md`) acumula appends indefinidamente se nada o compactar.
5. **Recall não é associativo.** Busca top-K retorna chunks isolados; nenhum mecanismo segue as ligações a partir dos hits para trazer o contexto vizinho relevante (a decisão ligada ao gotcha ligado ao projeto).

## Decisão

Adicionar ao vault uma **Camada Sináptica** (`_bootstrap/agentic/synapse/`): um motor de memória associativa que unifica semântica + grafo + uso, inspirado na fisiologia de memória humana (ativação que se propaga, sinapses que se fortalecem com co-ativação, poda do que não é usado, consolidação em "sono").

### Princípios (invariantes)

1. **Markdown continua sendo a fonte da verdade.** Toda camada derivada (SQLite, Qdrant, FalkorDB) é reconstruível a partir dos arquivos + log de ativações.
2. **Local-first**: nada sai da máquina; zero custo recorrente; sem API key obrigatória.
3. **Fail-soft**: com a stack offline, os comandos degradam para o comportamento anterior sem quebrar.
4. **Determinístico no retrieval**: nenhuma chamada de LLM no caminho de recall. LLM só em curadoria assistida.
5. **Consolidação nunca apaga**: compactar move para histórico; poda remove só arestas aprendidas; expiração move para lane `expired`.

### Arquitetura em 4 camadas

| Camada | Substrato | Papel |
|---|---|---|
| 0. Fonte da verdade | Markdown + WikiLinks + frontmatter | Memória canônica, human-editable |
| 1. Índice semântico | Qdrant + Ollama bge-m3 | "Essa lembrança se parece com o que procuro?" |
| 2. Grafo sináptico | SQLite (`_memory/.synapse/synapse.db`, canônico do estado sináptico) + projeção FalkorDB (superfície Cypher/MCP) | "Que lembranças essa lembrança puxa?" - nós = todas as notas; arestas tipadas com peso |
| 3. Fisiologia | Log de ativações (SQLite, append-only) + jobs de reforço/decay/consolidação | "O que fortalece, o que enfraquece, o que consolida" |

### Modelo de dados sináptico (SQLite)

- `nodes(id, path, slug, kind, project, title, created, updated, importance, updated_at)` - 1 nó por nota; `importance` = prior por kind (decision/learning > work-log).
- `edges(src, dst, kind, weight_base, boost, source, mentions, last_activated, updated_at)` - `kind` ∈ {WIKILINK, RELATED, REFERENCES, SUPERSEDES, TAG_SIBLING, STRUCTURAL, LEARNED}; `weight_base` deriva dos arquivos (rebuild sobrescreve), `boost` é aprendido por uso (decai).
- `activations(ts, node_id, source, session_id, query_hash)` - `source` ∈ {recall, search, read, write, session}; append-only.
- `falkor_tombstones` - deleções pendentes de propagação para a projeção.

### Algoritmos

- **Recall associativo** (`synapse recall`): (a) sementes = top-K do Qdrant (chunk→nota); (b) **spreading activation** 2-3 hops com amortecimento e normalização por grau; (c) score = α·semântico + β·ativação + γ·força (ativação-base estilo ACT-R: frequência × recência × importância). Saída inclui a **cadeia** que levou a cada memória e sugestões de próximo salto.
- **Reforço hebbiano** (`synapse reinforce`): memórias co-ativadas na mesma sessão fortalecem a aresta entre si (`Δw = η·(1-w)`); co-ativação repetida (≥3) entre nós NÃO ligados cria aresta `LEARNED` (sinaptogênese) - que aparece como sugestão de WikiLink real na curadoria.
- **Decay + poda** (`synapse decay`): `boost *= e^(-λ·Δt)` (meia-vida 90d); `LEARNED` abaixo do piso é podada; arestas `file` nunca somem pelo decay.
- **Consolidação "sono"** (`synapse consolidate`, semanal + sob demanda): compacta `current-state.md` (excedente vai íntegro para `current-state-history/`), expira capturas, detecta quase-duplicatas (proposta, gate humano), promove sinapses LEARNED a sugestões de link e reconcilia a projeção FalkorDB.
- **Projeção FalkorDB near-online**: sync incremental automático (delta via `updated_at` + tombstones) após cada `build`/`reinforce`/`decay`; reconciliação full no ciclo semanal. Consumidores Cypher/MCP enxergam o grafo atual; FalkorDB offline → skip fail-soft.

### Integração

1. **Hooks**: preflight de memória usa recall associativo; `PostToolUse` registra ativação de escrita e leitura de notas.
2. **Comandos**: `/recall` e `/consolidate` (paridade Codex `sb-recall`/`sb-consolidate`); `/ask` e `/justify` usam recall como fonte primária; `/end-session` roda o reforço da sessão (passo 8.75); cron semanal roda o ciclo completo.
3. **MCP** (`secondbrain-mcp`): tools `recall`, `memory_chain`, `reinforce`; `find_similar_decisions` semântico.

## Postgres: análise e veredito

Avaliado usar Postgres para os dados estruturados. **Veredito: não.** O que o vault precisa é event log + agregados de grafo, e o SQLite embarcado resolve com custo operacional zero, preservando local-first e o princípio de derivados reconstruíveis. Gatilhos para reavaliar: vault multi-host com writers concorrentes; >100k notas; consumo cross-serviço por outras aplicações.

## Consequências

**Ganhos:** recall associativo e explicável (memória puxa memória, com a cadeia visível); o uso vira sinal (o que se consulta junto se conecta; o que ninguém usa decai, sem apagar nada canônico); consolidação automática estanca o crescimento da memória de trabalho; MCP disponibiliza o recall para qualquer projeto.

**Trade-offs:** mais um substrato derivado (SQLite) - mitigado por rebuild determinístico e testes; pesos aprendidos são estado local da máquina (recomeçam neutros em máquina nova); recall custa ~+100-300ms sobre a busca pura.

**Reversibilidade:** fácil. Remover `_memory/.synapse/` + desativar hooks devolve o comportamento anterior; comandos degradam fail-soft.

## Alternativas consideradas

- **Estado sináptico canônico no FalkorDB**: quebraria o vault quando offline e não dá bom event log append-only. Mantido como projeção de consulta.
- **Pesos no frontmatter das notas**: poluiria as notas com estado de máquina e geraria churn de git a cada consulta.
- **LLM no caminho de recall (re-ranking)**: melhor qualidade marginal, mas quebra determinismo, latência e custo zero.

## Métricas de sucesso

- Recall@5 em queries de precedente ≥ busca vetorial pura (benchmark em `_bootstrap/agentic/eval/run_benchmark.py --engine both`).
- 100% dos comandos de memória fail-soft com stack offline (suite `synapse`).
- `current-state.md` compacto após consolidação, sem perda (histórico íntegro).
- Grafo sináptico cobre 100% das notas do vault.
