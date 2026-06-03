---
name: sb-tech-research
description: "Pesquise e avalie uma tecnologia, ferramenta ou approach técnico."
license: Apache-2.0
metadata:
  owner: second-brain
  vault: "$VAULT"
  vault_name: "Second Brain"
  vault_prefix: "sb"
  source_command: ".claude/commands/tech-research.md"
---

# Second Brain Tech Research

This is the Codex port of `tech-research` from `.claude/commands/tech-research.md`.

When the original command mentions `$ARGUMENTS`, treat it as the current user input or the text following the skill invocation.

Use `$VAULT` as the vault root for all relative paths unless the user provides another path.

Pesquise e avalie uma tecnologia, ferramenta ou approach técnico.

## Argumentos

$ARGUMENTS contém: [nome da tecnologia/ferramenta] [contexto de uso]
Exemplo: "Drizzle ORM para substituir Prisma" ou "Bun vs Node.js para nosso backend"

Se $ARGUMENTS estiver vazio ou incompleto, pergunte: "Qual tecnologia quer avaliar e em que contexto?"

## Passos

### 1. Consultar referências do vault

Ler em paralelo:
- `_knowledge/engineering/stack.md` - stack atual e decisões prévias (se existir)
- `_knowledge/engineering/architecture.md` - padrões de arquitetura atuais (se existir)
- `_knowledge/engineering/conventions.md` - convenções estabelecidas (se existir)
- `_knowledge/references.md` - ferramentas já catalogadas

### 1.5 Cruzar com vault via retrieval semântico

Antes de pesquisa externa, verificar se a tecnologia (ou similar) já foi pesquisada/adotada/descartada:

```bash
bash .claude/scripts/sb-search.sh "<tecnologia>" --kind features --k 5
bash .claude/scripts/sb-search.sh "<tecnologia>" --kind sources --k 5
bash .claude/scripts/sb-search.sh "<tecnologia>" --kind patterns --k 3
bash .claude/scripts/sb-search.sh "<tecnologia> decisão" --kind decisions --k 3
```

Se infra Qdrant indisponível, pular silenciosamente.

**Para resultados com score >= 0.55:**

| Caso | Reportar |
|---|---|
| Feature em `_features/` já documenta uso atual | "Já temos em produção em [[X]]" — pesquisa pode pivotar para 'evolução' não 'adoção' |
| Source em `_sources/` documenta avaliação prévia | "Já avaliamos em [[Y]] (data) — qual mudou desde então?" |
| Pattern em `_patterns/` define padrão alternativo já adotado | "Convenção atual é [[Z]] — proposta substitui ou complementa?" |
| ADR em `_decisions/` decidiu sobre o tema | Pode ser bloqueante — ler ADR antes de propor mudança |

Se vault já cobre a pergunta, **considerar não pesquisar externamente**. Reportar achados do vault e perguntar se ainda quer pesquisa nova.

### 2. Pesquisar a tecnologia

Buscar informações disponíveis:
- Documentação oficial: maturidade, features, API surface
- GitHub: stars, issues abertas, frequência de commits, bus factor
- Comunidade: Stack Overflow activity, Discord/forum size, blog posts recentes
- Benchmarks: performance comparada com alternativas (se disponível)
- Breaking changes: histórico de mudanças quebrando compatibilidade

### 3. Avaliar fit com o stack atual

Usando o contexto de `_knowledge/engineering/`:
- Compatível com o stack atual?
- Qual o custo de migração?
- Quais dependências introduz?
- Qual o impacto na DX (developer experience)?

### 4. Comparar alternativas

Listar 2-3 alternativas e comparar:

| Critério | [Tecnologia A] | [Tecnologia B] | [Tecnologia C] |
|----------|----------------|----------------|----------------|
| Maturidade | | | |
| Performance | | | |
| DX | | | |
| Comunidade | | | |
| Manutenção | | | |
| Custo de migração | | | |

### 5. Criar nota no pipeline

Criar `_pipeline/research-[nome-kebab-case].md`:

```yaml
---
tags: [pipeline, research, spike]
status: em-andamento
created: [data de hoje]
updated: [data de hoje]
---
```

Preencher: Informações Básicas, Contexto, Análise, Próximos Passos.
Adicionar seção Related com WikiLinks para [[stack]], [[architecture]].

### 6. Recomendação

Avaliar honestamente:
- **Adotar** - fit claro com o stack, comunidade saudável, resolve o problema
- **Prototipar** - promissor mas precisa de PoC antes de decidir
- **Monitorar** - interessante mas não é o momento (imaturidade, custo de migração alto)
- **Descartar** - não resolve o problema, ou alternativa é claramente superior

## Output

Responda **em português (BR)** com:

### Pesquisa Técnica - [Nome da Tecnologia]

**Resumo:** [O que é e por que estamos avaliando, em 2-3 frases]

**Análise:**

| Critério | Avaliação | Notas |
|----------|-----------|-------|
| Maturidade | [X/5] | [detalhe] |
| Performance | [X/5] | [detalhe] |
| DX | [X/5] | [detalhe] |
| Comunidade | [X/5] | [detalhe] |
| Fit com stack | [X/5] | [detalhe] |

**Comparação com alternativas:**
[Tabela comparativa]

**Trade-offs:**
- Prós: [lista]
- Contras: [lista]

**Recomendação: [Adotar / Prototipar / Monitorar / Descartar]**
[Justificativa com argumentos técnicos concretos]

**Próximo passo:** [Ação concreta - ex: "Criar PoC de migração num branch isolado"]

**Nota criada:** `_pipeline/research-[nome].md`

## Regras

- Dados antes de hype. Se todo mundo está falando sobre X mas os benchmarks não sustentam, diga.
- Nunca recomende adoção sem avaliar custo de migração e impacto no time.
- Se a tecnologia atual resolve bem o problema, diga isso. "Funciona" é uma resposta válida.
- Compare com alternativas reais, não com straw men.
- Se falta informação para uma avaliação sólida, diga o que falta e não force uma conclusão.
