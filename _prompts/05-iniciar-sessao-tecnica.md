# 05 — Protocolo de Início de Sessão Técnica

Use este prompt para maximizar a eficiência do contexto ao iniciar qualquer sessão técnica. Cole no Claude Code dentro do diretório `$VAULT` — ou leia este arquivo manualmente para decidir o que carregar.

---

## Por que este protocolo existe

Um vault em uso real pode ter dezenas a centenas de arquivos. Carregar tudo desperdiça janela de contexto. A maioria das sessões precisa de < 5 arquivos. Este protocolo define o que carregar em cada tipo de trabalho para chegar ao estado útil com menos de 40% da janela ocupada.

---

## Tabela de Sessão por Tipo

| Tipo de Sessão | Carregar Obrigatório | Carregar Condicional | Não Carregar |
|---|---|---|---|
| **Trabalho em projeto específico** | MASTER-INDEX + `project/README` | `project/modules` se toca módulos; `project/gotchas` se é bug | Outros projetos, features não relacionadas |
| **Implementar feature nova** | FEATURE-CATALOG + feature page mais próxima existente | Pattern page do padrão usado; `project/modules` para entender onde encaixa | ADRs antigos, outros projetos |
| **Decisão arquitetural cross-cutting** | PATTERN-MATRIX + `_patterns/{padrão}` | ADR existente se houver; READMEs dos projetos afetados | Features individuais, outros padrões |
| **Review de PR** | `project/gotchas` + `project/decisions` | Patterns usados no PR; feature pages referenciadas | Roadmap, integrações não afetadas |
| **Nova épica / spec** | `project/README` + `project/roadmap` | FEATURE-CATALOG (verificar se já existe); `project/decisions` (contexto anterior) | Outros projetos, patterns não relacionados |
| **Debug / incident response** | `project/gotchas` + `_memory/current-state` | `project/integrations` se falha em integração; `_patterns/{padrão-relacionado}` (ex.: outbox-inbox, idempotency) | Roadmap, outros projetos |

---

## Protocolo de 5 Passos

Execute na ordem — pare quando tiver contexto suficiente para a tarefa:

**Passo 1 — Sempre:**
```
Ler AGENTS.md + _memory/current-state.md (se existir)
```
Tempo: ~30 segundos. Dá: identidade, guardrails, contexto recente.

**Passo 2 — Se houver índice:**
```
Ler _index/MASTER-INDEX.md (se já populado)
```
Tempo: ~10 segundos. Dá: mapa do portfólio, onde está cada coisa.

**Passo 3 — Se trabalho em projeto:**
```
Ler _knowledge/projects/{projeto}/README.md
```
Tempo: ~15 segundos. Dá: quick stats, padrões usados, entry point para o que precisar.

**Passo 4 — Se trabalho em módulo específico:**
```
Ler _knowledge/projects/{projeto}/modules.md
```
Tempo: ~20 segundos. Dá: mapa de módulos com links para features.

**Passo 5 — Se vai implementar ou replicar feature:**
```
Ler _features/{slug}.md
```
Tempo: ~15 segundos. Dá: contrato, localização, como reusar, gotchas.

**Budget total de contexto:** < 40% da janela para navegação. > 60% reservado para o trabalho real.

---

## Sinais de que o vault está stale

Verifique `_memory/current-state.md`. Se a data de atualização for > 3 dias:
- As features em desenvolvimento podem ter avançado
- O roadmap pode estar desatualizado
- Decisões recentes podem não estar registradas

Ação: rodar `/end-session` ao final da próxima sessão produtiva para sincronizar.

---

## Quando fazer reset de contexto

Faça reset (nova sessão) quando:
- Mudou de projeto no meio da sessão e acumulou contexto irrelevante
- A janela está > 80% ocupada e ainda há trabalho pela frente
- A sessão misturou debug + feature + decisão arquitetural sem planejamento

Antes do reset, rodar `/end-session` para não perder o que foi decidido.

---

## Quando usar `/end-session`

Sempre ao final de:
- Sessão que resultou em código commitado
- Sessão que teve decisão arquitetural (mesmo sem código)
- Sessão que revelou um gotcha novo que outros devs precisam saber
- Mudança de projeto (antes de iniciar o próximo)

Não esperar o final do dia — o `/end-session` é por sessão temática, não por hora.

---

## Referência Rápida de Paths

```
Navegação:    _index/MASTER-INDEX.md
              _index/PATTERN-MATRIX.md
              _index/FEATURE-CATALOG.md

Projeto:      _knowledge/projects/{nome}/README.md
              _knowledge/projects/{nome}/modules.md
              _knowledge/projects/{nome}/gotchas.md
              _knowledge/projects/{nome}/decisions.md
              _knowledge/projects/{nome}/roadmap.md

Padrão:       _patterns/{nome}.md
Feature:      _features/{slug}.md

Memória:      _memory/current-state.md
Decisões:     _decisions/ADR-{XXXX}-{slug}.md
```
