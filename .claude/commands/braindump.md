Processe meu braindump e organize no vault.

## Argumentos

$ARGUMENTS contém o texto livre do braindump. Pode ser estruturado ou caótico, curto ou longo.

Se $ARGUMENTS estiver vazio, pergunte: "O que está na sua cabeça?"

## Passos

### 1. Capturar

Registre tudo que foi dito, sem filtrar ou julgar neste momento.

### 2. Criar nota de sessão

Crie `_sessions/[YYYY-MM-DD]-braindump.md` com:

```yaml
---
tags: [session, braindump]
status: active
created: [data de hoje]
updated: [data de hoje]
---
```

Conteúdo:
- **Raw dump:** O texto original, preservado integralmente
- **Itens identificados:** Lista categorizada (ver passo 3)
- **Conexões:** WikiLinks para notas existentes

Se já existir um braindump do mesmo dia, use sufixo: `[YYYY-MM-DD]-braindump-2.md`

### 3. Categorizar e conectar

Identifique no braindump:

| Categoria | Ação |
|-----------|------|
| **Decisão de arquitetura/design** | Criar ADR em `_decisions/` com contexto + alternativas + trade-offs |
| **Aprendizado técnico** | Criar ou atualizar nota em `_learnings/` |
| **Ideia de feature/projeto** | Marcar com tag #idea na nota de sessão |
| **Bug ou problema técnico** | Marcar com tag #urgent se precisa de ação imediata |
| **Tech debt identificado** | Atualizar `_knowledge/engineering/tech-debt.md` se existir |
| **Mudança em projeto** | Atualizar o projeto em `_knowledge/projects/{nome}/` |
| **Referência/recurso técnico** | Adicionar em `_knowledge/references.md` |
| **Observação sobre item do pipeline** | Atualizar nota em `_pipeline/` |
| **Reflexão pessoal/carreira** | Manter na nota de sessão |

### 3.5 Detecção de precedentes (retrieval semântico)

Antes de classificar como ADR/learning novo, verificar se já existe registro similar no vault.

Para cada item potencialmente classificável como ADR/learning/gotcha, rodar:

```bash
bash $VAULT/.claude/scripts/sb-search.sh "<descrição do item>" --kind decisions --k 3
bash $VAULT/.claude/scripts/sb-search.sh "<descrição do item>" --kind learnings --k 3
```

Se infra Qdrant indisponível, pular silenciosamente.

**Para resultados com score >= 0.55:**

| Caso | Ação |
|---|---|
| ADR existente cobre o tema (precedente claro) | NÃO criar novo ADR — anexar contexto ao existente via Edit OU sugerir `/justify <texto>` |
| Learning equivalente já registrado | Mesma lógica — atualizar existente em vez de duplicar |
| Apenas adjacente | Criar novo, mas linkar ao existente como `Related: [[X]]` |

Reportar ao usuário antes de salvar:

```
[braindump] Detectei possível duplicação:
- Sua decisão sobre "X" tem precedente em [[2026-04-11-cqrs-source-of-truth]] (score 0.71)
- Quer atualizar a existente, criar nova com link explícito, ou descartar?
```

### 3.6 Linkagem mínima (semantic anchoring)

Para cada nota criada/atualizada (após resolver duplicação acima), garantir linkagem mínima ao grafo:

- **≥1 link a `_patterns/`** se o conteúdo menciona padrão arquitetural
- **≥1 link a um projeto** em `_knowledge/projects/<projeto>/` quando relevante
- **≥1 link a `_decisions/` ou `_learnings/`** se relacionado a decisão/learning prévio

Tools disponíveis para descobrir candidatos:
- `bash $VAULT/.claude/scripts/auto-linker.sh --scope <path>` → mostra links sugeridos (dry-run)
- Ler `_index/PATTERN-MATRIX.md` ou `_index/CONCEPT-INDEX.md` para inspiração

Aplicar manualmente os WikiLinks antes de prosseguir. Não deixar nota nova como ilha (zero links de saída).

### 4. Atualizar estado

Se o braindump contém informação que muda o contexto atual:
- Atualize `_memory/current-state.md`
- Adicione à seção relevante (o que foi feito, decisões, próximos passos)

### 5. Registrar no activity log

Append em `_memory/activity-log.md`:
```
## [YYYY-MM-DD HH:MM] braindump | [resumo de 1 linha]
```

## Output

Responda **em português (BR)** com:

1. **Resumo:** O que entendi do braindump (2-3 frases)
2. **Itens acionáveis:** Lista com prioridade (alta/média/baixa)
3. **Notas criadas/atualizadas:** Quais arquivos foram tocados
4. **Conexões feitas:** WikiLinks identificados
5. **Provocação:** Se algo no braindump parece inconsistente com os objetivos atuais ou com decisões anteriores, diga — honestidade radical.

## Regras

- Nunca descarte nada — se foi dito, tem razão de ser.
- Ideias vagas ficam como #idea para revisão futura.
- Decisões técnicas firmes vão para `_decisions/` com data e contexto.
- Se algo contradiz uma ADR anterior, sinalize.
- Não invente conexões que não existem — só conecte se for genuíno.
