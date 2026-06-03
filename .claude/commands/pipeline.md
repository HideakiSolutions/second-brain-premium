Mostre o dashboard de projetos e tasks com visão completa e acionável.

## Passos

### 1. Coletar dados

Ler em paralelo:
- Todos os arquivos em `_pipeline/` (exceto `_exemplo.md`)
- `_memory/current-state.md`
- `_knowledge/projects.md`

Para cada nota no pipeline, extrair:
- Nome do item
- Tipo (projeto / task / spike / research / bug / feature)
- Status atual (do frontmatter ou da seção de informações)
- Prioridade
- Data de entrada
- Última ação (do Histórico - última entrada)
- Próximo passo

### 2. Classificar por prioridade de ação

Ordenar itens por urgência de ação:

1. **BLOQUEADO** - Itens com bloqueio ativo que impede progresso
2. **URGENTE** - Itens com ação atrasada ou parados há mais de 7 dias
3. **EM ANDAMENTO** - Itens com trabalho ativo
4. **REVIEW** - Itens aguardando revisão (PR, design review, feedback)
5. **BACKLOG** - Itens priorizados mas não iniciados
6. **CONCLUÍDO** - Itens concluídos recentemente (últimos 30 dias)
7. **ARQUIVO** - Itens arquivados (mostrar separado, resumido)

### 3. Calcular métricas

- Total de itens ativos (excluindo arquivados e concluídos)
- Itens por status
- Itens sem atualização há mais de 14 dias (stale)
- Taxa de conclusão (concluídos / total histórico)
- Itens sem próximo passo definido

## Output

Responda **em português (BR)** com:

### Pipeline - [data de hoje]

---

#### Alertas

Mostrar APENAS se houver itens:
- Itens bloqueados: "[Item] - bloqueado por [razão] - precisa de ação"
- Itens stale (14+ dias): "[Item] - última ação em [data] - precisa de atenção"
- Itens sem próximo passo: "[Item] - sem próximo passo definido"

Se não houver alertas: "Nenhum alerta."

---

#### Pipeline Completo

Tabela ordenada por prioridade de ação:

| # | Item | Tipo | Status | Prioridade | Última ação | Próximo passo |
|---|------|------|--------|------------|-------------|---------------|
| 1 | [nome] | [tipo] | [status] | [alta/média/baixa] | [data + resumo] | [ação concreta] |

---

#### Métricas

| Métrica | Valor |
|---------|-------|
| Itens ativos | [X] |
| Em review | [X] |
| Bloqueados | [X] |
| Stale (14+ dias) | [X] |
| Concluídos (último mês) | [X] |

---

#### Concluídos recentemente

Se houver itens concluídos nos últimos 30 dias:

| Item | Tipo | Data de conclusão |
|------|------|-------------------|
| [nome] | [tipo] | [data] |

Se não houver: omitir seção.

---

**Recomendação:** [Qual item merece atenção primeiro e por quê]

## Regras

- Seja direto - sem fluff, sem disclaimers.
- Se o pipeline está vazio, diga: "Pipeline vazio. Adicione itens em `_pipeline/`."
- Se algo está parado, destaque com urgência.
- Ordene SEMPRE por prioridade de ação, não por data.
- Não inclua `_exemplo.md` na contagem.
- Se um item está sem próximo passo definido, isso é um alerta.
