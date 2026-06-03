Gere um RFC (Request for Comments) ou design doc para uma decisão técnica.

## Argumentos

$ARGUMENTS contém: [título ou descrição da proposta]
Exemplo: "migrar autenticação de sessions para JWT" ou "implementar cache layer com Redis"

Se $ARGUMENTS estiver vazio, pergunte: "Qual é a proposta técnica? (descreva o problema e a solução que está considerando)"

## Passos

### 1. Carregar contexto

Ler em paralelo:
- `_knowledge/engineering/architecture.md` - padrões de arquitetura atuais (se existir)
- `_knowledge/engineering/stack.md` - stack atual (se existir)
- `_knowledge/engineering/conventions.md` - convenções (se existir)
- `_knowledge/projects.md` - projetos relacionados

### 1.5 Buscar precedentes via retrieval semântico

Antes de redigir, descobrir se já há decisão/learning aplicável. Rodar:

```bash
bash .claude/scripts/sb-search.sh "<tema da proposta>" --kind decisions --k 5
bash .claude/scripts/sb-search.sh "<tema da proposta>" --kind learnings --k 3
bash .claude/scripts/sb-search.sh "<tema da proposta>" --kind patterns --k 3
```

Se infra Qdrant indisponível, pular esta etapa silenciosamente e seguir para o passo 2.

Para cada resultado com `score >= 0.55`, classificar:

| Classificação | Quando |
|---|---|
| **Precedente** | Decisão/learning já cobre o tema, proposta atual é alinhada ou extensão |
| **Contradição** | Proposta atual conflita com decisão anterior — REQUER justificativa explícita |
| **Adjacente** | Tema próximo mas não decisivo — citar como contexto |

**Se houver Precedente** → considerar fortemente NÃO criar novo RFC. Em vez disso, sugerir ao usuário: "decisão similar em [[X]] — quer atualizar a existente em vez de criar nova?"

**Se houver Contradição** → o RFC DEVE ter seção "Contradição com ADR existente" listando o que muda e justificando.

### 2. Estruturar o RFC

Com base no contexto e na proposta:
- **Qual problema estamos resolvendo?** (não a solução, o problema)
- **Por que agora?** (o que mudou que torna isso necessário)
- **Quais abordagens foram consideradas?** (mínimo 2 alternativas)
- **Qual a proposta?** (a recomendação com justificativa)
- **Quais os trade-offs?** (o que estamos abrindo mão)
- **Qual o plano de migração?** (se aplicável)
- **Como validamos que funcionou?** (métricas de sucesso)

### 3. Avaliar impacto

- Quais sistemas/serviços são afetados?
- Qual o risco de breaking changes?
- Qual o esforço estimado? (T-shirt sizing: S/M/L/XL)
- É reversível? Se sim, qual o custo de reverter?

### 4. Criar nota no pipeline

Criar `_pipeline/rfc-[nome-kebab-case].md`:

```yaml
---
tags: [pipeline, rfc, architecture]
status: em-andamento
created: [data de hoje]
updated: [data de hoje]
---
```

### 5. Gerar o RFC

Escrever o documento completo seguindo o template abaixo.

## Output

Responda **em português (BR)** com:

### RFC: [Título da Proposta]

**Autor:** [[about-me]] | **Data:** [data de hoje] | **Status:** Draft

---

#### Precedentes detectados

[Listar com classificação. Exemplo:]

- **Precedente:** [[../_decisions/X|ADR-X]] — {1 frase do que aquela decisão estabeleceu}
- **Contradição:** [[../_decisions/Y|ADR-Y]] — {por que a proposta atual diverge}
- **Adjacente:** [[../_learnings/Z|Z]] — {contexto relacionado}

[Se nenhum precedente foi encontrado, escrever: "Nenhum precedente relevante no vault." e seguir.]

#### Contexto

[2-3 parágrafos explicando o problema atual, por que existe, e o que mudou que torna a solução necessária agora]

#### Proposta

[Descrição clara da solução proposta, com detalhes suficientes para implementar]

#### Alternativas consideradas

**Alternativa A: [nome]**
- Descrição: [o que seria]
- Prós: [lista]
- Contras: [lista]
- Por que não: [razão]

**Alternativa B: [nome]**
- Descrição: [o que seria]
- Prós: [lista]
- Contras: [lista]
- Por que não: [razão]

#### Trade-offs

| Ganho | Custo |
|-------|-------|
| [o que ganhamos] | [o que abrimos mão] |

#### Impacto

| Dimensão | Avaliação |
|----------|-----------|
| Sistemas afetados | [lista] |
| Esforço estimado | [S/M/L/XL] |
| Risco | [baixo/médio/alto] |
| Reversibilidade | [sim/parcial/não] |

#### Plano de migração

[Passos numerados para implementar, incluindo rollback plan]

1. [Passo 1]
2. [Passo 2]
3. [Passo 3]

#### Métricas de sucesso

[Como sabemos que funcionou - métricas concretas e mensuráveis]

---

**Nota criada:** `_pipeline/rfc-[nome].md`

**Próximo passo:** [Ação concreta - ex: "Revisar com o time", "Criar PoC", "Implementar"]

## Regras

- O RFC deve ser baseado em contexto real do vault e do stack atual.
- Sempre apresente pelo menos 2 alternativas consideradas (mesmo que claramente inferiores).
- Nunca minimize trade-offs. Se a proposta tem desvantagens, liste todas.
- Se não há informação suficiente para uma proposta sólida, diga o que precisa ser investigado primeiro.
- O tom deve ser técnico e objetivo - RFC não é pitch de vendas.
- Se a proposta contradiz uma ADR existente, sinalize explicitamente.
