# 02 — Como Documentar Nova Feature Reutilizável

Use este prompt quando uma feature implementada em um projeto for genérica o suficiente para ser reutilizada ou consultada em outros projetos. Cole no Claude Code dentro do diretório `$VAULT`.

---

Documente a feature `{SLUG_DA_FEATURE}` no knowledge graph do vault em `$VAULT`.

## Critério para criar uma feature page

Crie uma feature page se **qualquer** destas condições for verdadeira:
- Outro dev olharia essa implementação antes de decidir copiar ou reimplementar
- A feature envolve uma decisão não-óbvia (escolha de library, padrão de idempotência, estrutura de tabela)
- A feature aparece em 2+ projetos ou há plano concreto de reuso
- A feature é a implementação canônica de um padrão arquitetural do vault

Não crie feature page para CRUD trivial, endpoints padrão, ou qualquer coisa que um dev implementaria do zero em < 1 hora sem consultar nada.

---

## 1. Criar `_features/{slug}.md`

```yaml
---
tags: [feature, {categoria}]
pattern: {nome-do-pattern-pai}      # ex: outbox-inbox, saga-pattern
projects: [{projeto1}, {projeto2}]
status: production | poc | planned
created: {data}
---
```

Seções obrigatórias:

### `## What It Is`
Uma frase. O que a feature faz e qual problema resolve.

### `## Implementation Location`
Caminhos exatos no repositório primário:
```
{projeto}/src/Infrastructure/{Pasta}/
  {Arquivo}.cs   — {responsabilidade}
  {Arquivo2}.cs  — {responsabilidade}
```

### `## Core Contract`
O contrato essencial da feature — interface, SQL crítico, configuração mínima, ou o snippet que explica o "como funciona":
```csharp
// ou SQL, ou YAML — o que for mais revelador
```

### `## How to Reuse`
Passos numerados para replicar em outro projeto:
1. Copiar ou referenciar {arquivo}
2. Configurar {dependência}
3. Registrar no DI container via {método}
4. Invocar via {interface/método}

### `## Known Gotchas`
Armadilhas que causariam bugs ou horas de debug sem este aviso. Pelo menos 2 items.

### `## Projects Using This`
| Projeto | Localização | Notas |
|---------|-------------|-------|
| [[../projects/{nome}/README\|{nome}]] | `src/...` | variação ou detalhe |

### `## Pattern Reference`
→ [[../_patterns/{padrão}\|{Padrão}]] — como esta feature implementa o padrão

### `## Related Features`
→ [[{feature-relacionada}]] — por que estão conectadas

---

## 2. Atualizar `_index/FEATURE-CATALOG.md`

Adicionar nova linha na tabela da categoria correta:
```
| {slug} | {status} | `{projeto}/src/...` | {projeto1}, {projeto2} |
```

Se a categoria ainda não existe (nova área de domínio), criar seção nova no catálogo.

---

## 3. Atualizar a pattern page

Em `_patterns/{padrão-pai}.md`, seção `## Canonical Feature Implementations`:
```
→ [[../features/{slug}|{Nome Legível}]] — {projeto} ({status})
```

---

## 4. Atualizar o módulo do projeto

Em `_knowledge/projects/{projeto}/modules.md`, na linha do módulo relevante, atualizar coluna Feature Principal com link para a nova feature page.

---

## 5. Status correto

| Status | Quando usar |
|--------|-------------|
| `production` | Rodando em produção, battle-tested |
| `poc` | Funcional mas não em produção ainda |
| `planned` | Apenas definido, não implementado |

Nunca marcar como `production` se está apenas em staging ou POC.

---

## Checklist de qualidade

- [ ] `## What It Is` tem exatamente 1 frase?
- [ ] `## Implementation Location` tem caminhos reais (não genéricos)?
- [ ] `## Core Contract` tem um snippet que explica o funcionamento real?
- [ ] `## How to Reuse` tem passos que um dev seguiria sem perguntar nada?
- [ ] `## Known Gotchas` tem pelo menos 2 armadilhas reais?
- [ ] FEATURE-CATALOG atualizado?
- [ ] Pattern page atualizada em `## Canonical Feature Implementations`?
- [ ] Módulo do projeto linkado para a feature?
