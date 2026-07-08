---
name: sb-justify
description: "Recebe um trecho de proposta/decisão e classifica precedentes do vault como precedente | contradição | adjacente. Use antes de RFC ou braindump."
license: Apache-2.0
metadata:
  owner: second-brain
  vault: "$VAULT"
  vault_name: "Second Brain"
  vault_prefix: "sb"
  source_command: ".claude/commands/justify.md"
---

# Second Brain Justify

This is the Codex port of `justify` from `.claude/commands/justify.md`.

When the original command mentions `$ARGUMENTS`, treat it as the current user input or the text following the skill invocation.

Use `$VAULT` as the vault root for all relative paths unless the user provides another path.


# /justify

Crítico de propostas. Você recebe um trecho de proposta/decisão e cruza com o vault para detectar precedentes, contradições ou adjacências.

## Argumentos

`$ARGUMENTS` é o trecho da proposta em linguagem natural. Pode ser uma frase, parágrafo ou esboço de RFC.

Exemplo:
```
/justify "Vamos migrar de PostgreSQL para EventStoreDB no meu-projeto para ter event sourcing nativo"
```

## Passos

### 1. Pré-flight

Validar infra:
```bash
bash .claude/scripts/sb-reindex.sh status
```

Se Qdrant offline, parar e instruir: `bash _bootstrap/agentic/stack.sh start`.

### 2. Identificar conceitos centrais

Da proposta, extrair 2-4 termos-chave para busca. Exemplos:
- "migrar de PostgreSQL para EventStoreDB" → ["postgresql", "eventstoredb", "event sourcing", "migração de banco"]
- "adotar Kong como gateway no lugar de YARP" → ["kong", "yarp", "api gateway"]

### 3. Buscar precedentes (paralelo)

Para cada termo, rodar o **recall associativo** em múltiplos kinds (fonte primária - as sinapses puxam a decisão-mãe mesmo quando o hit direto é uma nota derivada):

```bash
bash .claude/scripts/sb-synapse.sh recall "<termo 1>" --kind decisions --k 5
bash .claude/scripts/sb-synapse.sh recall "<termo 1>" --kind learnings --k 3
bash .claude/scripts/sb-synapse.sh recall "<termo 1>" --kind patterns --k 3
```

Aproveitar a `cadeia` de cada resultado para identificar o ADR de origem quando o hit for indireto. Fallback: se o grafo sináptico estiver ausente, usar `sb-search.sh` com os mesmos filtros.

Concatenar resultados, deduplicar por arquivo, manter score máximo.

### 4. Ler fontes com score >= 0.55

Para cada fonte qualificada, `Read` do arquivo (parcial via heading_path se possível) para entender o que ela estabelece.

### 5. Classificar cada fonte

| Classificação | Critério |
|---|---|
| **Precedente** | A decisão/learning anterior já decidiu sobre o tema, e a proposta atual é alinhada ou extensão. |
| **Contradição** | A proposta atual contradiz a decisão anterior. Bloqueante OU requer revogação explícita do ADR. |
| **Adjacente** | Tema próximo mas a fonte não decide sobre o ponto da proposta atual. Citar como contexto. |

Critérios para decidir:
- ADR define "MUST X" e proposta diz "vamos fazer Y" onde Y ≠ X → **Contradição**
- ADR define "X é opt-in" e proposta diz "ativar X em projeto Z" → **Precedente**
- Learning relata "tentamos X e deu errado" e proposta sugere X → **Contradição** com história
- Pattern documenta solução para problema da proposta → **Precedente**

### 6. Sintetizar veredicto

Estrutura obrigatória:

```
## Análise da proposta

> {citação curta da proposta original}

## Precedentes

- ✓ **[[../_decisions/X|ADR-X]]** ({score}) — {1-2 frases do que estabelece e por que é precedente}
- ✓ **[[../_learnings/Y|Y]]** — {idem}

## Contradições

- ✗ **[[../_decisions/Z|ADR-Z]]** ({score}) — {o que diverge}
  - **Implicação:** {revogar ADR? justificar exceção? abandonar proposta?}

## Adjacências (contexto)

- · **[[../_patterns/W|W]]** — {tangência relevante}

## Veredicto

Uma das três:
- **PROSSEGUIR** — proposta tem precedente claro e nenhuma contradição
- **AJUSTAR** — há pontos a alinhar com decisões existentes (listar)
- **BLOQUEADO** — contradição com ADR ativo. Antes de prosseguir, decidir: revogar ADR, fazer exceção justificada, ou abandonar proposta.

## Próxima ação

{1 frase concreta — ex: "Atualizar [[../_decisions/X]] em vez de criar nova" ou "Escrever RFC com seção 'contradição com ADR-Y'"}
```

## Regras

- **Sem fonte → sem afirmação.** Score >= 0.55 é mínimo para citar.
- **Honestidade radical** — se a proposta tem contradição clara, dizer. Não suavizar.
- **Idioma:** PT-BR.
- **Tom:** crítico construtivo. Apontar problemas é a função.

## Quando usar

- Antes de `/rfc` quando a proposta é não-trivial
- Antes de `/braindump` quando o item parece controverso
- Após `/tech-research` quando o veredicto é "Adotar" e quer-se validar contra ADRs
- Quando o usuário diz "tenho uma ideia, mas não sei se já decidi algo"
