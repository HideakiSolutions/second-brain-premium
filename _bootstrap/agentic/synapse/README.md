# `synapse/` — Camada Sináptica (memória associativa)

Motor de memória associativa do second brain: transforma o vault de "notas com links" em um grafo de memórias com fisiologia — sinapses tipadas com peso, que fortalecem com uso (reforço hebbiano), enfraquecem com desuso (decay), nascem de co-ativação (sinaptogênese) e passam por consolidação periódica ("sono").

**ADR:** `_decisions/2026-07-08-camada-sinaptica-memoria-associativa.md`

## Modelo mental

| Cérebro | Aqui |
|---|---|
| Neurônio / memória | Nota markdown (nó) |
| Sinapse | Aresta tipada com peso (`WIKILINK`, `RELATED`, `SUPERSEDES`, `STRUCTURAL`, `TAG_SIBLING`, `LEARNED`) |
| Disparo | Ativação (read/write/search/recall registrados em event log) |
| "Fire together, wire together" | `reinforce`: co-ativação aumenta `boost` da aresta; 3+ co-ativações entre notas não-ligadas criam aresta `LEARNED` |
| Esquecimento gradual | `decay`: `boost *= e^(-ln2/90d · Δt)`; `LEARNED` abaixo de 0.15 é podada |
| Lembrança puxa lembrança | `recall`: sementes semânticas (Qdrant) + spreading activation 2 hops sobre os pesos |
| Sono / consolidação | `consolidate`: compacta current-state, expira capturas, propõe merges e novos links, reconcilia FalkorDB |

## Invariantes

1. **Markdown é a fonte da verdade.** O SQLite (`_memory/.synapse/synapse.db`, gitignorado) é derivado; `build` o reconstrói dos arquivos. Só o log de ativações é dado primário novo (da máquina).
2. **Determinístico**: zero LLM no caminho de recall. Mesma query → mesmo resultado.
3. **Fail-soft**: recall semântico exige Qdrant+Ollama e retorna erro acionável offline; `--seed`, `explain`, `reinforce`, `decay` e `build` são 100% locais.
4. **Consolidação nunca apaga**: compactar move para `current-state-history/`; poda remove apenas arestas `LEARNED`; propostas (merge, link) têm gate humano.

## Arquivos

| Arquivo | Papel |
|---|---|
| `db.py` | Schema/estado SQLite: `nodes`, `edges(weight_base, boost)`, `activations`, `coactivations`, tombstones |
| `extract.py` | Vault → nós + arestas `file` (reusa convenções do chunker: `kind`, `source_file`) |
| `recall.py` | Recall associativo (sementes Qdrant → spreading activation → score composto) + `explain` (caminho mais forte entre duas memórias) |
| `physiology.py` | `activate`, `reinforce` (hebbiano + sinaptogênese), `decay` (+ poda) |
| `falkor_sync.py` | Projeção near-online no FalkorDB: incremental (delta + tombstones) e full (reconciliação) |
| `consolidate.py` | Ciclo de sono: compact, expire, dedup, propostas, reconciliação FalkorDB, report |
| `main.py` | CLI `synapse` (wrapper: `.claude/scripts/sb-synapse.sh`) |

## Score de recall

```
score = 0.55·semântico + 0.30·ativação_propagada + 0.15·força
força  = saturação(ln(1 + Σ (dias_desde_ativação + 0.1)^-0.5)) × importância_do_kind
```

- Propagação com amortecimento 0.6/hop e normalização por grau (hubs não inundam).
- `importância`: decisions 1.30 > learnings 1.25 > patterns 1.20 > ... > work-log 0.80 > pipeline 0.60.
- Cada resultado inclui a **cadeia** (`seed → intermediária → memória`) e sugestões de próximo salto.

## Uso

```bash
bash .claude/scripts/sb-synapse.sh build                       # reconstrói grafo (idempotente)
bash .claude/scripts/sb-synapse.sh recall "query" --k 8        # recall associativo
bash .claude/scripts/sb-synapse.sh recall --seed <slug>        # expansão a partir de uma nota (offline)
bash .claude/scripts/sb-synapse.sh explain <slug-a> <slug-b>   # como duas memórias se conectam
bash .claude/scripts/sb-synapse.sh reinforce --window 480      # reforço hebbiano da janela
bash .claude/scripts/sb-synapse.sh decay                       # esquecimento gradual
bash .claude/scripts/sb-synapse.sh sync-falkor [--full]        # projeção FalkorDB sob demanda
bash .claude/scripts/sb-synapse.sh consolidate                 # ciclo de sono completo
bash .claude/scripts/sb-synapse.sh status                      # estatísticas
```

Slash commands: `/recall`, `/consolidate` (Codex: `sb-recall`, `sb-consolidate`).

## Integrações automáticas

| Ponto | O quê |
|---|---|
| Hook `PostToolUse` (Read) | `sb-synapse-activate.sh read` — leitura de nota do vault registra ativação |
| Hook `PostToolUse` (Write/Edit) | `on-post-tool-use.sh` → ativação `write` (além da fila de reindex) |
| Preflight de memória (`on-prompt-submit`) | `memory_reviewer.preflight` usa recall associativo (`--no-log` para não reforçar por injeção ambiente) com fallback sb-search → grep |
| `/end-session` (passo 8.75) | `build` + `reinforce` — consolida o sinal hebbiano da sessão |
| Cron segunda 09:45 | `weekly-synapse-consolidate.sh` — build → reinforce → decay → consolidate |
| MCP `secondbrain-mcp` | Tools `recall`, `memory_chain`, `reinforce`; `find_similar_decisions` semântico |
| FalkorDB graph `synapse` | Projeção **near-online** com pesos: sync incremental automático após `build`/`reinforce`/`decay` (delta via `updated_at` + tombstones de deleção); reconciliação full no consolidate semanal. Desative o autosync com `SB_SYNAPSE_AUTOSYNC=0` (os testes usam). FalkorDB offline → skip fail-soft |

## Testes

```bash
bash tests/test-synapse.sh     # ou tests/run-all.sh (suite `synapse`)
```

Cobrem: build tipado, recall offline por seed com cadeia, fail-soft com stack offline, sinaptogênese na 3ª co-ativação, poda por decay, compactação sem perda.
