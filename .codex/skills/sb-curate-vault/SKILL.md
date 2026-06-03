---
name: sb-curate-vault
description: "Revisão interativa de propostas de curação do vault"
license: Apache-2.0
metadata:
  owner: second-brain
  vault: "$VAULT"
  vault_name: "Second Brain"
  vault_prefix: "sb"
  source_command: ".claude/commands/curate-vault.md"
---

# Second Brain Curate Vault

This is the Codex port of `curate-vault` from `.claude/commands/curate-vault.md`.

When the original command mentions `$ARGUMENTS`, treat it as the current user input or the text following the skill invocation.

Use `$VAULT` as the vault root for all relative paths unless the user provides another path.


# /curate-vault

Você é o curador interativo do second-brain. Seu papel é apresentar as propostas geradas pelo self-curation agent e registrar a decisão humana em cada uma.

## Protocolo

### 1. Gerar novas propostas

Execute o scan para detectar novas oportunidades:

```bash
bash .claude/scripts/curator.sh scan
```

### 2. Ler propostas pendentes

Leia `_pipeline/curation-proposals.md` e filtre apenas as propostas com status `[ ]` (pendente).

Para cada proposta pendente, apresente:
- **Título** da proposta
- **Tipo** (H1/H2/H3/H4/H5/H6/H7) com descrição do que significa
- **Corpo** completo da proposta
- **Opções:** [a]ceitar / [r]ejeitar / [s]kip

### 3. Registrar decisão

Após o usuário decidir, atualize o marcador no arquivo `_pipeline/curation-proposals.md`:

- **Aceitar `[a]`:** Substituir `[ ]` por `[x]` na linha `**Status:**`
- **Rejeitar `[r]`:** Substituir `[ ]` por `[~]` e adicionar linha `**Razão:** <motivo informado pelo usuário>`
- **Skip `[s]`:** Deixar `[ ]` sem alteração, passar para a próxima

### 4. Se aceito — gerar nota guia (opcional)

Se o usuário aceitar e quiser implementar imediatamente:

- **H1 (novo pattern):** Criar rascunho de `_patterns/<slug>.md` com frontmatter correto e seções: Contexto, Problema, Solução, Quando Usar, Trade-offs, Projetos que Usam
- **H2 (nota órfã):** Sugerir qual arquivo editar para adicionar o backlink
- **H3 (nova tag):** Editar `_index/TAG-TAXONOMY.md` adicionando a tag na seção apropriada
- **H4 (decisão obsoleta):** Sugerir revisão do ADR com nova seção `## Revisão YYYY-MM-DD`
- **H5 (pattern sem ADR):** Criar ADR em `_decisions/` documentando a adoção formal do pattern
- **H6 (contradição entre ADRs):** Revisar o ADR mais antigo e adicionar seção `## Supersede` se necessário
- **H7 (gap de adoção):** Avaliar no contexto do projeto-alvo se o pattern se aplica; se sim, adicionar edge `USES_PATTERN` no grafo

### 5. Limpeza pós-revisão

Após processar todas as propostas, perguntar ao usuário se deseja limpar as propostas resolvidas:

```bash
bash .claude/scripts/curator.sh clear
```

## Tipos de proposta

| Tipo | Descrição |
|------|-----------|
| H1 | Cluster de learnings com alta similaridade semântica → candidato a novo `_pattern/` |
| H2 | Nota recente sem nenhum backlink → possível nota órfã ou link faltando |
| H3 | Tag usada em 4+ arquivos mas fora da taxonomia → candidata a entrar em `TAG-TAXONOMY.md` |
| H4 | ADR `active` com mais de 120 dias + ADR mais recente com termos de revogação → possível obsolescência |
| H5 | Pattern usado em 3+ projetos mas com menos de 3 referências em Decisions/Learnings → documentar em ADR (graph-aware) |
| H6 | Dois ADRs referenciando o mesmo Pattern com gap >60 dias → possível contradição ou atualização necessária (graph-aware) |
| H7 | Pattern adotado em 4+ projetos de um domínio, ausente em outro projeto do mesmo domínio → gap de adoção (graph-aware) |

## Guardrails

- **Nunca** modifique `_patterns/`, `_decisions/`, `_learnings/` sem confirmação explícita do usuário
- Apenas `_pipeline/curation-proposals.md` e, se aceito, o arquivo-alvo da ação
- Toda modificação deve ser mínima e reversível
- Se o usuário rejeitar, registrar a razão para que a heurística aprenda
