---
name: sb-ask
description: "Pergunte qualquer coisa ao second brain. Resposta sintetizada via busca semântica + leitura de fontes, sempre com referências verificáveis."
license: Apache-2.0
metadata:
  owner: second-brain
  vault: "$VAULT"
  vault_name: "Second Brain"
  vault_prefix: "sb"
  source_command: ".claude/commands/ask.md"
---

# Second Brain Ask

This is the Codex port of `ask` from `.claude/commands/ask.md`.

When the original command mentions `$ARGUMENTS`, treat it as the current user input or the text following the skill invocation.

Use `$VAULT` as the vault root for all relative paths unless the user provides another path.


# /ask

Q&A agêntico sobre o vault. Você é o agente cognitivo do second brain.

## Argumentos

`$ARGUMENTS` é uma pergunta em linguagem natural. Pode incluir nome de projeto:
- `/ask meu-projeto "qual o estado atual?"` → focus em projeto meu-projeto
- `/ask "decisões sobre auth"` → vault inteiro
- `/ask meu-projeto "quão próximo do MVP?"` → análise de progresso

## Passos

### 1. Pré-flight

Validar que infra está rodando:
```bash
bash .claude/scripts/sb-reindex.sh status
```

Se Qdrant ou Ollama estiverem offline, parar e informar usuário (sugerir `cd _bootstrap/agentic && docker compose up -d`).

### 2. Detectar intenção (intent dispatch)

Identifique a natureza da pergunta para escolher estratégia de busca:

| Sinal na pergunta | Intent | Filtros sb-search |
|---|---|---|
| "estado atual", "fase", "onde estamos" | state | `--kind projects` se projeto identificado |
| "próximo passo", "próximas atividades", "o que falta" | progress | `--kind projects` + `--k 8` para puxar work-log e roadmap |
| "decisão", "ADR", "por que decidimos" | decisions | `--kind decisions --k 6` |
| "aprendizado", "learning", "como evitar" | learnings | `--kind learnings --k 6` |
| "padrão", "qual padrão", "como fazer X" | patterns | `--kind patterns --k 5` |
| "feature", "já implementamos X" | features | `--kind features --k 5` |
| "quão próximo do objetivo", "distância" | progress + state combinados | dois calls de sb-search |
| "quando", "histórico", "evolução" | timeline | sem filtro, k=10 + ordenar por data |
| "bloqueio", "gotcha", "armadilha" | blockers | `--kind` em projects + busca por gotchas |
| pergunta genérica | general | sem filtro, k=10 |

Se a pergunta cita projeto explícito (ex: `meu-projeto`, `meu-projeto`), adicionar `--project <slug>`.

### 3. Executar busca semântica

```bash
bash .claude/scripts/sb-search.sh "<query reformulada>" [--kind X] [--project Y] [--k N]
```

Você pode rodar **múltiplas buscas paralelas** se a pergunta tem múltiplos componentes (ex: pergunta de progresso → uma busca em projects, outra em decisions pendentes).

### 4. Ler fontes verificáveis

Para cada um dos top-3 resultados de sb-search, decidir:
- Se o snippet (200 chars) já responde → não ler arquivo, citar direto
- Se precisa contexto → `Read` do arquivo (com offset/limit no heading_path se possível)

**Não invente conteúdo.** Toda afirmação na resposta deve estar ancorada em chunk recuperado ou arquivo lido.

### 5. Sintetizar resposta

Estrutura mínima:

```
## Resposta

{Síntese em 2-4 parágrafos. Concisa. Direta. Sem corporate speech.}

## Fontes

- [[<wikilink-do-arquivo>]] — {1 frase do que aquela fonte contribuiu}
- [[<wikilink>]] — {idem}

## Lacunas detectadas (se houver)

- {O que a pergunta queria que NÃO foi encontrado, ou sinais de informação obsoleta}
```

### 6. Casos especiais

#### Pergunta sobre "quão próximo do objetivo X está?"
Estratégia:
1. `sb-search` no kind=projects para puxar state + roadmap
2. Read do `_knowledge/projects/<X>/roadmap.md` (objetivos vs entregue)
3. Read do `_knowledge/projects/<X>/state.md` (fase atual)
4. Cruzar: contar tarefas marcadas concluídas vs total no roadmap
5. Reportar % com lista das 3-5 tarefas-chave restantes

#### Pergunta sobre "tenho dúvida X — já decidi algo similar?"
Estratégia:
1. `sb-search "<dúvida>" --kind decisions --k 5`
2. Read dos 2-3 ADRs com score >0.55
3. Para cada ADR: classificar como **precedente** (alinhado), **contradição** (decisão atual conflita) ou **adjacente** (tema próximo, não decide)
4. Reportar com classificação visível

#### Pergunta vaga ("o que está rolando?")
Estratégia:
1. Ler `_memory/current-state.md` (já carregado pelo hook em sessões diárias)
2. Sintetizar últimos 3 entries
3. Sem busca semântica desnecessária

### 7. Registrar no activity log

Append em `_memory/activity-log.md`:
```
## [YYYY-MM-DD HH:MM] ask | {projeto ou —} — {pergunta resumida em 60 chars}
```

## Regras

- **Sempre cite fontes** — sem fonte, não afirme
- **Detecte staleness** — se um learning ou decision tem `updated:` >180 dias, sinalize "informação possivelmente desatualizada"
- **Seja honesto sobre lacunas** — se sb-search retornou nada relevante, diga "vault não tem informação sobre X"
- **Não invente links** — só cite WikiLinks de arquivos que aparecem em sb-search ou Read
- **Tom**: direto, sem floreio, sem "vou procurar para você", sem "ótima pergunta"
- **Idioma**: português (BR)

## Output esperado

Resposta com fontes em ≤ 30 segundos. Se demorar mais, há algum problema (Ollama travado, infra fora).
