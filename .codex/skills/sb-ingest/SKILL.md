---
name: sb-ingest
description: "Você é o ingestor de fontes externas do segundo cérebro. Capture, estruture e conecte a fonte ao vault."
license: Apache-2.0
metadata:
  owner: second-brain
  vault: "$VAULT"
  vault_name: "Second Brain"
  vault_prefix: "sb"
  source_command: ".claude/commands/ingest.md"
---

# Second Brain Ingest

This is the Codex port of `ingest` from `.claude/commands/ingest.md`.

When the original command mentions `$ARGUMENTS`, treat it as the current user input or the text following the skill invocation.

Use `$VAULT` as the vault root for all relative paths unless the user provides another path.

Você é o ingestor de fontes externas do segundo cérebro. Capture, estruture e conecte a fonte ao vault.

## Argumentos

$ARGUMENTS contém a fonte: URL, caminho de arquivo local, ou texto raw colado diretamente.

Se $ARGUMENTS estiver vazio, pergunte: "Qual fonte quer ingerir? (URL, caminho de arquivo ou texto)"

## Passos

### 1. Capturar o conteúdo

- Se URL: usar WebFetch para buscar o conteúdo
- Se caminho de arquivo: usar Read para ler o arquivo
- Se texto raw: usar o texto diretamente de $ARGUMENTS

### 2. Extrair e estruturar

Analisar o conteúdo e extrair:
- **Claims principais:** afirmações centrais do autor
- **Entidades relevantes:** tecnologias, padrões, ferramentas mencionadas
- **Decisões ou recomendações:** o que o autor recomenda fazer ou evitar
- **Aprendizados acionáveis:** o que muda na forma de trabalhar se você acreditar nisso

### 3. Criar nota em `_sources/`

Criar `_sources/[YYYY-MM-DD]-[slug].md` onde slug é kebab-case do título ou tema principal.

```yaml
---
tags: [source, ingest, {categoria}]
source_url: {url ou "local" ou "raw"}
source_type: {article | video-transcript | docs | paper | raw | book}
author: {autor se disponível, ou "desconhecido"}
ingested: {data de hoje}
status: active
---
```

Seções da nota:
- `## Resumo` — 3-5 frases: o que é, quem escreveu, por que importa
- `## Claims Principais` — bullet list dos argumentos centrais
- `## Aprendizados Acionáveis` — o que fazer diferente após ler isso
- `## Conexões com o Vault` — WikiLinks para padrões, features ou projetos relacionados
- `## Contradições` — se contradiz alguma decisão em `_decisions/`, listar aqui com link

### 4. Cross-linkar com o vault

Para cada conceito ou tecnologia relevante:
- Verificar se existe arquivo em `_patterns/` → linkar usando path válido
- Verificar se existe em `_features/` → linkar usando path válido
- Verificar se existe projeto em `_knowledge/projects/{projeto}/{projeto}.md` → linkar
- Verificar se existe learning relacionado em `_learnings/` → linkar
- Verificar se contradiz algum ADR em `_decisions/` → sinalizar explicitamente

**Regra anti-grafo-quebrado:** nunca criar WikiLink para conceito que ainda não tem arquivo canônico. Se a fonte menciona um conceito útil mas inexistente (`semantic-routing`, `parallel-agents`, etc.), registrar como texto simples e adicionar observação "ainda sem nota canônica no vault". Não usar placeholders como `[[X]]`, `[[topic-name]]` ou paths inventados.

**Linkagem mínima obrigatória:** toda nota criada em `_sources/` deve ter pelo menos:
- 1 link para projeto, pattern, feature, decision ou learning existente
- 0 WikiLinks quebrados no arquivo recém-criado

### 5. Decidir absorção de conhecimento (apenas para fontes de terceiros)

Se a fonte for de terceiros (não é conteúdo próprio do dono do vault), perguntar:

> "Quer absorver o conhecimento desta fonte em `_learnings/`? (s/n)"
> "Se sim, extraio os insights acionáveis e crio um arquivo em `_learnings/` — o `/content-idea` vai considerá-los ao gerar novas ideias."

**Se sim:** criar `_learnings/[slug].md` com:
```yaml
---
tags: [learning, source-based, {categoria}]
source: _sources/[slug].md
ingested: {data de hoje}
status: active
---
```
Seções:
- `## Insight Central` — a ideia mais importante em 1-2 frases
- `## O que muda na prática` — bullet list: o que fazer diferente após absorver isto
- `## Conexões` — WikiLinks apenas para padrões, decisões ou projetos existentes

Antes de concluir, validar os links do arquivo novo:

```bash
bash $VAULT/.claude/scripts/graph-metrics.sh
grep -A40 "## Broken links" $VAULT/_memory/graph-metrics.md
```

Se o arquivo recém-criado aparecer em `Broken links`, corrigir antes de responder.

**Se não:** encerrar — o arquivo em `_sources/` é suficiente. Não criar `_learnings/`.

### 6. Registrar no activity log

Append em `_memory/activity-log.md`:
```
## [YYYY-MM-DD HH:MM] ingest | [slug] — [fonte resumida em < 60 chars]
```

## Output

Responda **em português (BR)** com:

### Ingestão: [título ou slug]

**Fonte:** [URL ou tipo]
**Arquivo criado:** `_sources/[slug].md`

**Resumo:**
[3-5 frases do que foi ingerido]

**Claims principais:**
[Lista dos argumentos centrais]

**Conexões com o vault:**
[WikiLinks identificados]

**Contradições detectadas:**
[Se contradiz alguma decisão existente, detalhar. Se nenhuma, omitir.]

**Ações sugeridas:**
[O que fazer com este conhecimento — criar learning? atualizar feature? abrir decisão?]

## Regras

- Nunca inventar informações que não estão na fonte
- Se a fonte for muito longa, focar nas partes mais relevantes para o domínio atual do vault
- Contradições com decisões existentes devem ser sinalizadas, não ignoradas
- Slug do arquivo: kebab-case, sem caracteres especiais, máximo 50 chars
