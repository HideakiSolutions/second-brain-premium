# `_bootstrap/agentic/` — Stack Semântico Opcional

Stack local de busca semântica + style profiler + curator + predictor. Tudo opcional: o vault funciona sem este stack, apenas com qualidade inferior em alguns comandos.

## Visão Geral

| Componente | Função | Tipo | Externa? |
|---|---|---|---|
| `indexer/` | Chunking de markdown + push para Qdrant via embeddings Ollama | Python | depende Qdrant + Ollama |
| `synapse/` | **Camada sináptica**: grafo nota-a-nota com sinapses tipadas+peso, recall associativo (spreading activation), reforço hebbiano, decay e consolidação — ver `synapse/README.md` | Python | recall por query depende Qdrant + Ollama; resto é 100% local (SQLite) |
| `graph/` | Cliente FalkorDB para a projeção do grafo sináptico (graph `synapse`) | Python | depende FalkorDB (opcional, fail-soft) |
| `mcp/secondbrain-mcp/` | MCP server: recall associativo + grafo como tools para qualquer sessão | Node | depende FalkorDB; tools de recall dependem da stack |
| `eval/` | Benchmark de qualidade do retrieval | Python | depende indexer |
| `curator/` | Heurísticas de curadoria (clusters, órfãos, tags, stale ADRs) | Python | standalone (com FalkorDB opcional, atualmente removido) |
| `style/profiler.py` | Style profiler empírico dos seus artigos | Python | standalone |
| `predictor/` | Sugestões de próximas tasks via heurísticas + LLM | Python | usa Anthropic API se `ANTHROPIC_API_KEY` setada; cai para fallback determinístico sem |
| `stack.sh` | Gerencia Qdrant + Ollama em modo **docker** ou **nativo** (setup/start/stop/status) | Bash | modo docker requer Docker; modo nativo não |
| `docker-compose.yml` | Definição dos containers (usado pelo `stack.sh` no modo docker) | Docker | requer Docker daemon |
| `docker-compose.gpu.yml` | Override de GPU NVIDIA para o ollama (aplicado quando `SB_STACK_GPU=on`) | Docker | requer NVIDIA Container Toolkit |

---

## Por que Qdrant + Ollama?

### O que faz

Os comandos `/ask`, `/search`, `/justify`, `/densify`, `/learn-loop` consultam o vault via **busca semântica** (não só grep). Para isso:

1. **Ollama** roda o modelo de embeddings `bge-m3` localmente. Cada nota do vault vira um vetor de 1024 dimensões.
2. **Qdrant** armazena esses vetores e responde a queries de similaridade em ~10ms.

A query do usuário (ex.: "como tratamos idempotência em sagas?") vira embedding via Ollama, depois Qdrant retorna as N notas mais similares semanticamente — mesmo que não compartilhem palavras-chave exatas.

### Por que adotar

- **Recall semântico**: encontra a decisão certa mesmo quando você não lembra o nome exato. `"problema de duplicação em fila"` recupera `_decisions/idempotency-keys.md` sem precisar de "idempotency" na query.
- **Local-first**: nada sai da sua máquina. Vault sensível continua privado. Sem custo de API.
- **Baixo footprint**: Qdrant + Ollama + modelo bge-m3 cabem em ~3GB de disco e <1GB de RAM em idle. Embeddings via CPU rodam em <100ms por documento (GPU NVIDIA acelera).
- **Determinístico**: a mesma query produz os mesmos top-K resultados sempre. Não há temperatura/randomness.

### Quando NÃO usar

- Você só vai ter <50 documentos no vault (grep resolve)
- Trabalha numa máquina muito restrita (<2GB RAM disponível)
- Prefere consultas só via comandos LLM puros (`/ask` cai para fallback grep + Read)

(Docker deixou de ser exigência: o modo **nativo** roda Qdrant binário + Ollama direto no SO.)

### Trade-offs

| Aspecto | Pró | Contra |
|---|---|---|
| Setup | Um `stack.sh setup`; <10 min para estar operacional | Adiciona Qdrant+Ollama ao seu ambiente (via Docker ou nativo, à sua escolha) |
| Recall | Encontra coisas que grep não acharia (sinônimos, paráfrases) | Falsos positivos em queries genéricas — precisa filtrar por `--kind` ou `--project` |
| Manutenção | Reindex incremental via `/reindex`; ~5s para o vault inteiro | Precisa rerodar `/reindex` após mudanças grandes |
| Privacidade | 100% local; embeddings e índice nunca saem do disco | Modelos open-source (bge-m3) — não state-of-the-art como modelos proprietários |
| Performance | <100ms por query mesmo com 10k documentos | CPU embedding ocupa 1 core por ~100ms por documento na ingestão |
| Custo | Zero recorrente; só elétrica da máquina | ~3GB de disco + ~512MB de RAM em idle |

### Alternativas consideradas

- **OpenAI embeddings**: melhor qualidade marginal, mas $0.13/1M tokens, expõe vault a terceiros, e adiciona latência de rede. Evitado: contraria princípio "local-first".
- **SQLite + FTS5**: muito mais leve, mas só keyword search — perdeu recall semântico que é a razão de existir do stack.
- **DuckDB com extension vss**: viável, mas Qdrant tem ecossistema mais maduro (filtros nested, payload em JSON, REST API) e fica trivial trocar de embedder.
- **FalkorDB para grafo de relacionamentos**: estava aqui antes; removido por adicionar 3º serviço sem ganho proporcional. Pode voltar se você precisar de queries de grafo (e.g., "padrões usados em 3+ projetos do mesmo domínio").

---

## Como usar

### Escolher o modo (uma vez)

O `install.sh` pergunta o modo e grava em `stack.env` (por máquina, gitignorado):

```
SB_STACK_MODE=docker   # docker | native
SB_STACK_GPU=off       # on | off
```

- **docker** — Qdrant + Ollama em containers (binds em 127.0.0.1: Qdrant `6333`/`6334`, Ollama `11434`)
- **native** — binário oficial do Qdrant (baixado para `native/`, gitignorado) + Ollama instalado no SO. Sem virtualização: GPU dedicada é usada diretamente pelo Ollama.

Os dois modos compartilham o storage em `data/qdrant` (mesma versão do Qdrant nos dois) — dá para alternar sem reindexar.

### Setup (primeira vez)

```bash
bash _bootstrap/agentic/stack.sh setup
```

Baixa imagens/binários e o modelo `bge-m3` (~1.2GB na primeira vez). No modo nativo, se o Ollama não estiver instalado, o script orienta a instalação por plataforma. Se o registry do Ollama estiver inacessível na sua rede, o script mostra o fallback: GGUF do Hugging Face + `ollama create`.

### Subir / parar

```bash
bash _bootstrap/agentic/stack.sh start
bash _bootstrap/agentic/stack.sh stop     # docker: compose stop; nativo: só processos que o script subiu
bash _bootstrap/agentic/stack.sh status
```

### Indexar o vault

```bash
bash .claude/scripts/sb-reindex.sh
```

Para incremental:
```bash
bash .claude/scripts/sb-reindex.sh --since 7d
```

### Buscar

```bash
bash .claude/scripts/sb-search.sh "como tratamos idempotencia" --k 5
```

Ou via slash command no Claude Code:
```
/search como tratamos idempotência --kind decisions
/ask qual o estado atual do projeto X
```

### Verificar saúde

```bash
bash .claude/scripts/sb-reindex.sh status
```

### Remover (apaga dados indexados)

```bash
# modo docker:
docker compose -f _bootstrap/agentic/docker-compose.yml down -v
# modo nativo: pare a stack e apague o storage
bash _bootstrap/agentic/stack.sh stop && rm -rf _bootstrap/agentic/data/qdrant _bootstrap/agentic/native
```

---

## Fallback quando o stack está offline

Todos os comandos que dependem do stack semântico **degradam graciosamente**:

| Comando | Com stack | Sem stack |
|---|---|---|
| `/ask` | Busca semântica + síntese | Grep + Read em diretórios |
| `/search` | Top-K vetorial com score | Grep com `--include` |
| `/justify` | Precedentes via similaridade | Grep em `_decisions/` |
| `/densify` | Sugestões via similaridade | Pula |
| `/learn-loop` | Análise via embeddings | Heurísticas determinísticas |
| `/predict` | Se `ANTHROPIC_API_KEY` setada, usa Claude | Heurísticas frequência + roadmap |
| `/style-profile` | Style profiler empírico | Análise direta dos arquivos |

Você pode rodar o vault inteiro sem nunca subir Docker. O stack está aqui para quem quer **recall semântico + qualidade superior em sugestões**.

---

## Módulos internos

| Pasta | Função |
|---|---|
| `indexer/chunker.py` | Quebra markdown em chunks com heurísticas (headers, parágrafos, tabelas) |
| `indexer/store.py` | Clientes HTTP para Qdrant e Ollama |
| `indexer/main.py` | CLI: `index`, `search`, `status` |
| `synapse/main.py` | CLI: `build`, `recall`, `explain`, `activate`, `reinforce`, `decay`, `sync-falkor`, `consolidate`, `status` |
| `synapse/README.md` | Espec completa da camada sináptica (modelo, score, integrações) |
| `graph/falkor_client.py` | Cliente FalkorDB (redis-py com fallback RESP2 raw socket) |
| `eval/run_benchmark.py` | Roda queries-gabarito contra a collection (crie seu `benchmark.jsonl`) |
| `curator/main.py` | CLI: `scan` (gera propostas), `report`, `clear` |
| `curator/heuristics.py` | H1-H7: clusters, órfãs, tags, stale ADRs, etc. Algumas heurísticas (H5-H7) requerem FalkorDB e ficam desativadas sem ele |
| `style/profiler.py` | Lê `_content/articles/` e gera `fingerprint.json` (em-dashes, tropes, voz) |
| `predictor/main.py` | CLI de predição de próximas tasks por projeto |
| `predictor/llm_analyst.py` | Wrapper Claude/Anthropic com fallback determinístico |

---

## GPU (opcional)

bge-m3 roda bem em CPU. Com GPU NVIDIA (>4GB VRAM), embeddings aceleram ~5x — ingestão de 1000 documentos cai de ~2 minutos para ~25 segundos. Configure `SB_STACK_GPU=on` em `stack.env` (o installer pergunta, com default por auto-detecção de `nvidia-smi`):

- **Modo docker**: o `stack.sh` aplica o override `docker-compose.gpu.yml` automaticamente. Requer NVIDIA Container Toolkit no host.
- **Modo nativo**: o Ollama detecta e usa a GPU sozinho — sem camada de virtualização no caminho. Com `SB_STACK_GPU=off`, o `stack.sh` força CPU (oculta as GPUs via env) ao subir o `ollama serve`. Se o Ollama roda como serviço do SO, gerencie a GPU pela config do próprio serviço.

---

## Resumo: quando ativar este stack

✅ **Sim, ative se:**
- Você tem 100+ notas e quer recall semântico
- Quer privacidade total (nada sai da máquina)
- Quer commands `/ask`, `/search`, `/justify` com qualidade superior
- Tem ~6GB de disco livre (Docker OU modo nativo — você escolhe)

❌ **Não, deixe desligado se:**
- Vault tem <50 notas — grep + Read resolvem
- Trabalha numa máquina restrita
- Aceita os fallbacks determinísticos
