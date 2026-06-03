---
tags: [template, governance, project]
status: active
created: 2026-05-07
updated: 2026-05-07
---

# `_template/` — Template Canônico de Projeto

> Pasta de referência. Não editar para um projeto real — copiar e renomear.

## Como usar

1. Copiar a pasta para o nome do projeto:
   ```bash
   cp -r _knowledge/projects/_template _knowledge/projects/<projeto-slug>
   cd _knowledge/projects/<projeto-slug>
   ```
2. Renomear `_template.md` → `<projeto-slug>.md`:
   ```bash
   mv _template.md <projeto-slug>.md
   ```
3. Substituir todos os `{{PLACEHOLDERS}}` em cada arquivo (busca rápida: `grep -r '{{' .`).
4. Apagar este `README.md` da cópia.
5. Atualizar `_index/MASTER-INDEX.md` e `_index/CONCEPT-INDEX.md` para incluir o novo projeto.
6. Rodar `/lint` para verificar conformidade estrutural.

## Arquivos do template (estrutura mínima)

| Arquivo | Propósito | Obrigatório |
|---------|-----------|-------------|
| `<projeto>.md` | README/índice — quick stats, stack, patterns, features, how-to-run, deep-dive | ✅ |
| `state.md` | Estado atual: fase + próximo passo. Atualizado por `/end-session` e hooks. | ✅ |
| `modules.md` | Tabela de módulos/serviços com responsabilidade + features reutilizáveis | ✅ |
| `decisions.md` | ADRs vinculados (tabela) + decisões projeto-específicas | ✅ |
| `gotchas.md` | Itens numerados com armadilhas e regras não-óbvias | ✅ |
| `integrations.md` | Sistemas externos consumidos/expostos: tabela + tópicos de mensageria | ✅ |
| `roadmap.md` | Fases com objetivo + checklist + status atual | ✅ |
| `work-log.md` | Append-only table de unidades de trabalho. Atualizado por `/end-session`. | ✅ |

## Frontmatter padrão

```yaml
---
tags: [project-index, wiki, project, <domain>]   # domain: fintech, crypto, trading, ai-sdlc, automation, etc
status: active                                    # active | completed | archived
created: YYYY-MM-DD
---
```

`state.md` usa frontmatter mínimo:
```yaml
---
updated: YYYY-MM-DD
---
```

`work-log.md` adiciona `updated: YYYY-MM-DD`.

## Convenções de WikiLinks

Sempre usar paths relativos a partir da pasta do projeto (3 níveis acima para alcançar `_patterns/`, `_features/`, `_decisions/`):

```markdown
[[../../../_patterns/hexagonal-architecture|Hexagonal]]
[[../../../_features/marten-event-store|Marten Event Store]]
[[../../../_decisions/2026-04-11-hexagonal-architecture-mandatory|ADR-0001]]
```

Links internos do projeto (mesma pasta) sem path:
```markdown
[[modules]] · [[integrations]] · [[gotchas]] · [[decisions]] · [[roadmap]]
```

## Validação

O comando `/lint` (e o cron `weekly-vault-lint`) reportam:

- Projetos com `_knowledge/projects/<x>/` que não têm os 8 arquivos obrigatórios.
- Frontmatter ausente ou malformado.
- WikiLinks quebrados.
- Tags fora da `_index/TAG-TAXONOMY.md`.

Esta convenção é referenciada pelo ADR `2026-05-07-relacao-starter-vs-privado.md` (governance privado vs starter).
