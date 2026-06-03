Você é o segundo cérebro operacional. Gere o briefing diário.

## Passos

### 0. Verificar pré-condições (emitir ANTES de qualquer conteúdo do briefing)

**0a. Capturas pendentes (prioridade máxima)**

Contar linhas com `status: pendente-revisao` nos arquivos `_pipeline/inbox/auto-captures-*.md`:

```bash
grep -c "status: pendente-revisao" $VAULT/_pipeline/inbox/auto-captures-*.md 2>/dev/null | awk -F: '{sum+=$2} END {print sum+0}'
```

Se N > 0: emitir como **PRIMEIRO bloco do briefing**, em destaque:

> ⚠️ **N capturas pendentes em `_pipeline/inbox/`.**
> Execute `/review-captures` ANTES de ler as prioridades do dia.
> Essas capturas podem mudar o estado do portfólio.

Não omitir este bloco mesmo que pareça ruído — é o sinal mais importante do dia.

**0b. Flags de sessões anteriores**

- Se `$VAULT/_memory/.needs-end-session` existir:
  → Avisar: "**Atenção:** a última sessão foi encerrada sem `/end-session`. Contexto pode estar desatualizado. Execute `/end-session` para sincronizar antes de continuar."
  → Não apagar o flag — apenas o `/end-session` o remove.

- Se `$VAULT/_memory/.compacted-without-end-session` existir:
  → Avisar: "**Atenção:** houve compactação de contexto em uma sessão anterior sem `/end-session` prévio. Parte do contexto pode ter se perdido."
  → Não apagar o flag.

### 1. Leia `$VAULT/_memory/current-state.md` para entender o contexto recente.
2. Leia `$VAULT/_index/MASTER-INDEX.md` para ter o mapa atual do portfólio.
3. Para cada projeto marcado como ativo ou dev no MASTER-INDEX, leia o respectivo `$VAULT/_knowledge/projects/{nome}/{nome}.md` e extraia: fase atual, próximo passo, bloqueios.
4. Liste os arquivos em `$VAULT/_decisions/` — identifique decisões dos últimos 7 dias.
5. Liste os arquivos em `$VAULT/_learnings/` — identifique insights recentes relevantes para o dia.
6. Verifique conteúdo pendente:
   - Leia os arquivos em `$VAULT/_content/series/` — séries ativas com peças em rascunho. Extraia: próxima publicação sugerida e cadência.
   - Leia arquivos em `$VAULT/_content/articles/` com `status: rascunho` ou `status: revisao` que **não pertençam a nenhuma série ativa** — listar como rascunhos avulsos.

## Output

Responda **em português (BR)** com este formato:

### Briefing — [data de hoje]

**Estado atual:**
[Resumo de 2-3 frases do current-state.md — o que está acontecendo agora, em que fase está o trabalho]

**Portfólio ativo:**

| Projeto | Fase | Próximo passo | Bloqueios |
|---------|------|---------------|-----------|
| [nome] | [fase do README] | [ação concreta] | [bloqueio ou "nenhum"] |

Incluir apenas projetos com status `active` ou `dev ativo` no MASTER-INDEX. Omitir POCs pausados e projetos em espera.

**Decisões recentes:**
[Lista de decisões dos últimos 7 dias com data e resumo de 1 linha, ou "Nenhuma decisão recente."]

**Prioridades do dia:**
[3-5 itens ordenados por impacto, baseados nos projetos ativos e estado atual. Cada item deve ser uma ação concreta com referência ao projeto.]

1. [Ação — Projeto — por que é prioridade agora]
2. [Ação — Projeto — por que é prioridade agora]
3. [Ação — Projeto — por que é prioridade agora]

**Séries em andamento:**
[Para cada série em `_content/series/` com peças ainda não publicadas: nome da série, próxima peça sugerida (tipo + título), e cadência recomendada. Formato: "▶ [título da peça] ([tipo]) — publicar [quando, ex: hoje ou até sexta]". Se nenhuma série ativa, omitir.]

**Rascunhos avulsos:**
[Artigos/postagens em `_content/articles/` com status `rascunho` ou `revisao` que não pertencem a nenhuma série. Listar título e tipo. Se nenhum, omitir esta seção.]

**Alerta direto:**
[Se há algo crítico, atrasado, padrão preocupante, ou projeto sem progresso há mais de uma semana — diga sem rodeios. Se está tudo no caminho, omita esta seção.]

## 6. Registrar no activity log

Append em `$VAULT/_memory/activity-log.md`:
```
## [YYYY-MM-DD HH:MM] session-start | Briefing diário gerado
```

## Regras

- Não leia todos os projetos — apenas os ativos segundo o MASTER-INDEX.
- Se o current-state.md estiver desatualizado (última atualização > 3 dias), avisar antes do briefing.
- Não invente dados — use apenas o que está nos arquivos.
- Seja direto — sem fluff, sem disclaimers.
- Se o MASTER-INDEX não existir ainda, avisar e sugerir rodar o prompt `04-diagnostico-vault.md`.
