# `_bootstrap/agentic/` — Stack Semântico Opcional

Stack local de busca semântica + style profiler + curator + predictor. Tudo opcional: o vault funciona sem este stack, apenas com qualidade inferior em alguns comandos.

## Visão Geral

| Componente | Função | Tipo | Externa? |
|---|---|---|---|
| `indexer/` | Chunking de markdown + push para Qdrant via embeddings Ollama | Python | depende Qdrant + Ollama |
| `eval/` | Benchmark de qualidade do retrieval | Python | depende indexer |
| `curator/` | Heurísticas de curadoria (clusters, órfãos, tags, stale ADRs) | Python | standalone (com FalkorDB opcional, atualmente removido) |
| `style/profiler.py` | Style profiler empírico dos seus artigos | Python | standalone |
| `predictor/` | Sugestões de próximas tasks via heurísticas + LLM | Python | usa Anthropic API se `ANTHROPIC_API_KEY` setada; cai para fallback determinístico sem |
| `docker-compose.yml` | Sobe Qdrant + Ollama em containers locais | Docker | requer Docker daemon |

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
- Não quer adicionar Docker ao stack pessoal
- Trabalha numa máquina muito restrita (<2GB RAM disponível)
- Prefere consultas só via comandos LLM puros (`/ask` cai para fallback grep + Read)

### Trade-offs

| Aspecto | Pró | Contra |
|---|---|---|
| Setup | Um `docker compose up -d`; <10 min para estar operacional | Requer Docker; adiciona dependência ao seu ambiente |
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

### Subir o stack

```bash
docker compose -f _bootstrap/agentic/docker-compose.yml up -d
```

Sobe dois containers (binds em 127.0.0.1):
- `sb-qdrant` em `6333` (REST) e `6334` (gRPC)
- `sb-ollama` em `11434`

### Baixar o modelo de embeddings

```bash
docker exec sb-ollama ollama pull bge-m3
```

(~1.2GB de download na primeira vez.)

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

### Desligar (preserva dados)

```bash
docker compose -f _bootstrap/agentic/docker-compose.yml stop
```

### Remover (apaga dados indexados)

```bash
docker compose -f _bootstrap/agentic/docker-compose.yml down -v
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
| `eval/run_benchmark.py` | Roda queries-gabarito contra a collection (crie seu `benchmark.jsonl`) |
| `curator/main.py` | CLI: `scan` (gera propostas), `report`, `clear` |
| `curator/heuristics.py` | H1-H7: clusters, órfãs, tags, stale ADRs, etc. Algumas heurísticas (H5-H7) requerem FalkorDB e ficam desativadas sem ele |
| `style/profiler.py` | Lê `_content/articles/` e gera `fingerprint.json` (em-dashes, tropes, voz) |
| `predictor/main.py` | CLI de predição de próximas tasks por projeto |
| `predictor/llm_analyst.py` | Wrapper Claude/Anthropic com fallback determinístico |

---

## GPU (opcional)

bge-m3 roda bem em CPU. Se você tem GPU NVIDIA (>4GB VRAM), descomente o bloco `deploy.resources` em `docker-compose.yml` para acelerar embeddings em ~5x. Sem GPU, ingestão de 1000 documentos leva ~2 minutos; com GPU, ~25 segundos.

---

## Resumo: quando ativar este stack

✅ **Sim, ative se:**
- Você tem 100+ notas e quer recall semântico
- Quer privacidade total (nada sai da máquina)
- Quer commands `/ask`, `/search`, `/justify` com qualidade superior
- Tem Docker disponível e 6GB de disco livre

❌ **Não, deixe desligado se:**
- Vault tem <50 notas — grep + Read resolvem
- Não pode/quer rodar Docker
- Trabalha numa máquina restrita
- Aceita os fallbacks determinísticos
