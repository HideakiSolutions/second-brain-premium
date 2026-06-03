# 03 — Como Documentar Novo Padrão Arquitetural

Use este prompt quando um padrão cross-cutting novo precisar ser registrado no vault. Cole no Claude Code dentro do diretório `$VAULT`.

---

Documente o padrão `{NOME_DO_PADRAO}` no knowledge graph do vault em `$VAULT`.

## Critério para criar um pattern page

Crie uma pattern page se **qualquer** destas condições for verdadeira:
- O padrão aparece em 2+ projetos do portfólio (mesmo com variações de implementação)
- Um ADR mandatório do portfólio exige o padrão como default
- A ausência de documentação canônica causaria implementações divergentes nos projetos

Não crie pattern page para: frameworks/libraries (são tool, não padrão), convenções de código local, ou escolhas de nomenclatura.

---

## 1. Criar `_patterns/{nome}.md`

```yaml
---
tags: [pattern, architecture, {categoria}]
status: active
created: {data}
---
```

Seções obrigatórias:

### `## What It Solves`
2-3 frases: qual problema de design ou operacional este padrão resolve. Seja específico ao contexto do portfólio — não definições genéricas de livro.

### `## How It Works Here`
Como o padrão é implementado no portfólio especificamente. Incluir:
- Snippet de código ou diagrama ASCII que mostre a estrutura essencial
- **Regras específicas** — bullet list de decisões específicas que diferem do padrão genérico

### `## Projects Using This Pattern`
| Projeto | Uso | Variação/Notas |
|---------|-----|----------------|
| [[../projects/{nome}/README\|{nome}]] | {o que usa} | {full/partial/adapted} |

### `## Canonical Feature Implementations`
Links para as feature pages que implementam este padrão:
```
→ [[../features/{slug}|{Nome}]] — {projeto} ({status})
```
(Preencher depois de criar as feature pages correspondentes)

### `## Decision Records`
Links para ADRs que governam este padrão:
```
→ [[../_decisions/{slug}|ADR-XXXX: Título]] — {data}
```
Se não há ADR, criar um em `_decisions/` antes de finalizar esta page.

### `## When NOT to Use`
Lista concreta de contextos onde este padrão NÃO deve ser aplicado. Exemplos: domínios sem necessidade de consistência forte, serviços CRUD simples, projetos com baixo volume e SLA permissivo.

### `## Related Patterns`
Links para padrões complementares ou alternativos:
```
→ [[{padrão}]] — {relação: "implementa via", "alternativa quando", "usado junto com"}
```

---

## 2. Atualizar `_index/PATTERN-MATRIX.md`

Adicionar nova linha na tabela com o padrão e o status em cada projeto:
```
| {Padrão} | full | — | partial | — | — | — | — | — | — | — |
```
Valores: `full` | `partial` | `adapted` | `—`

---

## 3. Atualizar `_index/MASTER-INDEX.md`

Adicionar nova linha na tabela de padrões:
```
| [[../_patterns/{nome}\|{Nome}]] | {O que resolve em 1 frase} | {projetos principais} |
```

---

## 4. Atualizar READMEs dos projetos afetados

Em `_knowledge/projects/{projeto}/README.md`, seção `## Quick Stats`, linha Patterns:
```
- Patterns: [[../../_patterns/hexagonal-architecture|Hexagonal]] · [[../../_patterns/{nome}|{Nome}]] · ...
```

---

## 5. Criar ou linkar o ADR

Todo padrão novo deve ter ou linkar um ADR em `_decisions/`. Formato do ADR:

```markdown
---
tags: [decision, architecture]
status: active
created: {data}
---
# ADR-{XXXX}: {Título}

## Contexto
Por que esta decisão foi necessária.

## Decisão
O que foi decidido.

## Consequências
- Positivas: ...
- Negativas/Trade-offs: ...

## Reversibilidade
Fácil / Difícil / Irreversível — e o motivo.
```

---

## Checklist de qualidade

- [ ] `## How It Works Here` tem um snippet ou exemplo concreto do portfólio (não genérico)?
- [ ] `## Regras específicas` tem pelo menos 3 decisões específicas do portfólio?
- [ ] `## When NOT to Use` tem pelo menos 2 contextos concretos?
- [ ] PATTERN-MATRIX atualizado com o novo padrão?
- [ ] MASTER-INDEX atualizado?
- [ ] READMEs dos projetos afetados atualizados?
- [ ] ADR existe e está linkado?
- [ ] Links bidirecionais: projetos apontam para o padrão E o padrão aponta para os projetos?
