Você é o fechador de sessão do segundo cérebro. Consolide o trabalho feito, detecte o contexto e sincronize com o vault.

## Argumentos

$ARGUMENTS pode conter o nome do projeto trabalhado (ex: `/end-session meu-projeto`).
Se vazio, detecte o projeto pelo contexto da conversa atual.

Projetos conhecidos: `meu-projeto` `meu-projeto` `meu-projeto` `meu-projeto` `meu-projeto` `event-platform` `ai-engineering-orchestrator` `agentic-chain` `mcp-factory` `platform-gitops`

---

## Passos

### 1. Detectar contexto

a) Se $ARGUMENTS tem nome de projeto, usar esse nome.
b) Se vazio, analisar a conversa: qual projeto foi discutido? Qual codebase foi tocada?
c) Se nenhum projeto identificado: executar fluxo genérico sem atualização de projeto específico.

### 2. Classificar a sessão

Analisar toda a conversa e identificar:

**Tipo de trabalho:** escolher o tipo dominante. Se a sessão produziu ≥2 tipos distintos (ex: refactor + feature nova), registrar duas linhas no work-log — uma por tipo — com descrições separadas. Não colapsar em um único registro genérico.

| Tipo | Quando usar |
|------|-------------|
| `epic` | Workflow HSEOS ativo, múltiplas fases, epic ID identificável |
| `feature` | Nova funcionalidade implementada (novo endpoint, módulo, serviço) |
| `story` | Implementação de uma história dentro de um epic |
| `task` | Configuração, setup, scaffolding, documentação técnica |
| `fix` | Correção de bug, ajuste de comportamento, hotfix |
| `chore` | Refactor, cleanup, atualização de dependências, ajustes de CI |
| `spike` | Investigação, POC, exploração técnica sem implementação final |
| `session` | Trabalho genérico sem tipo específico (planejamento, revisão, conversa) |

**O que foi feito:** lista de ações concretas (arquivos criados/editados, código implementado, decisões tomadas)
**Gotchas descobertos:** bugs, comportamentos não-óbvios, armadilhas encontradas
**Decisões tomadas:** arquiteturais, estratégicas, de design
**Pendências:** o que ficou pela metade ou foi anotado para depois
**Bloqueadores identificados:** qualquer menção a "bloqueado", "blocker", serviço unhealthy, dependência externa não resolvida, ou item marcado como EM ESPERA. Listar aqui — serão propagados ao `state.md` no Step 6a.
**PRs abertas/fechadas nesta sessão:** listar `#NNN — título — [aberta/mergeada/fechada]` — serão propagadas ao `state.md`.
**Branch feature ativa ao encerrar:** registrar se houver — será propagada ao `state.md`.
**Validações de fechamento:** listar testes, smoke, HSEOS gates, validação distribuível e qualquer limitação objetiva.

---

### 3. Verificar registro do projeto no vault

Se projeto foi identificado no Passo 1:

Verificar se `$VAULT/_knowledge/projects/{projeto}/` existe.

**Se existir:** ir para Passo 4.

**Se NÃO existir:** auto-registrar o projeto antes de continuar.

#### Auto-registro (executar apenas se pasta não existe)

1. Tentar ler `<projects-root>/{projeto}/CLAUDE.md` — extrair stack, domínio e contexto
2. Tentar ler `<projects-root>/{projeto}/.hseos/config/hseos.config.yaml` — extrair metadados
3. Criar 7 arquivos em `_knowledge/projects/{projeto}/`:

**{projeto}.md** (índice do projeto) — inferir da conversa e dos arquivos lidos:
```yaml
---
tags: [wiki, project, {categoria inferida}]
status: active
created: {data de hoje}
---
```
Seções: What It Is, Quick Stats (stack, fase, padrões observados), Key Features, How to Run (se conhecido), Deep Dive (links para os outros 6 arquivos)

**Regra de cluster:** `{projeto}.md` é o hub local. Todos os arquivos criados no diretório do projeto devem linkar de volta para `[[{projeto}]]`, e o Deep Dive do hub deve linkar `[[modules]]`, `[[integrations]]`, `[[gotchas]]`, `[[decisions]]`, `[[roadmap]]`, `[[work-log]]` e `[[state]]`.

**modules.md** — com módulos/serviços observados na sessão (pode ser incompleto)

**integrations.md** — dependências externas observadas

**gotchas.md** — gotchas encontrados nesta sessão (mínimo 1 se houver)

**decisions.md** — decisões desta sessão

**roadmap.md** — fase atual inferida

**work-log.md** — criar com a entrada desta sessão já incluída:
```yaml
---
tags: [project, work-log]
status: active
created: {data de hoje}
---
# Work Log
> Tipos: epic feature story task fix chore spike session

| Data | Tipo | Descrição | Epic ID | Status |
|------|------|-----------|---------|--------|
```

4. Atualizar `_index/MASTER-INDEX.md` — adicionar linha do novo projeto
5. Atualizar `_index/PATTERN-MATRIX.md` — nova coluna com `—` para todos os padrões inicialmente
6. Registrar no activity log: `## [YYYY-MM-DD] update | Auto-registro: {projeto} adicionado ao vault`

---

### 4. Registrar unidade de trabalho no work-log

Antes de fazer append, checar se já existe entrada com a mesma data e tipo similar no arquivo. Se existir entrada do mesmo dia com tipo idêntico, atualizar a linha existente em vez de adicionar nova linha.

Append em `$VAULT/_knowledge/projects/{projeto}/work-log.md`:

```
| {YYYY-MM-DD} | {tipo} | {descrição concisa de 1 linha} | {epic-id ou —} | concluído |
```

Se a sessão produziu ≥2 tipos distintos, registrar uma linha por tipo.

Se a sessão foi interrompida sem conclusão, usar `em andamento` no lugar de `concluído`.

---

### 5. Atualizar arquivos granulares do projeto

Baseado no tipo de trabalho e conteúdo da sessão:

**Gotchas descobertos** → criar arquivo detalhado em `_knowledge/projects/{projeto}/gotchas/{YYYY-MM-DD-slug}.md` e atualizar o manifesto `_knowledge/projects/{projeto}/gotchas.md` com link + resumo:
```
---
tags: [project, gotchas, {projeto}]
status: active
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
project: {projeto}
gotcha_date: {YYYY-MM-DD}
---

# {Título curto}
**Problema:** O que acontece se você não souber isso
**Solução/Contexto:** Como funciona de fato
```

**Decisões arquiteturais locais** → criar arquivo detalhado em `_knowledge/projects/{projeto}/decisions/{YYYY-MM-DD-slug}.md` e atualizar o manifesto `_knowledge/projects/{projeto}/decisions.md` com link + resumo:
```
# {Título da Decisão}
**Contexto:** Por que essa decisão foi necessária
**Decisão:** O que foi decidido
**Consequências:** Trade-offs e o que mudou
**Reversibilidade:** Fácil / Difícil / Irreversível
```

Regra de progressive disclosure: `decisions.md` e `gotchas.md` são manifestos enxutos. Não adicionar histórico longo diretamente neles. Para escrita automatizada, preferir `.claude/scripts/lib/vault_writer.py append-gotcha` e `append-project-decision`.

**Atualizar `roadmap.md` — sempre** quando a sessão produziu código, PRs, decisões ou bloqueadores. Ler o arquivo atual primeiro, preservar seções históricas/planejamento não tocadas e atualizar apenas status atual, PRs abertas/fechadas nesta sessão, bloqueadores ativos e próximos passos concretos. Exceção: sessão do tipo `session` puramente conversacional sem código ou decisão — nesse caso omitir se o arquivo já existir e não houver nada novo a registrar.

**Feature nova reutilizável** → verificar se merece feature page (critério: outro dev consultaria antes de reimplementar?). Se sim, sugerir: "Criar `_features/{slug}.md` seguindo `_prompts/02-onboarding-nova-feature.md`"

**Linkagem mínima do projeto:** para qualquer arquivo granular atualizado (`state`, `modules`, `decisions`, `gotchas`, `integrations`, `roadmap`, `work-log`), garantir:
- link de retorno para o hub local `[[{projeto}]]`, exceto quando o arquivo já é o hub
- links para patterns/features/decisions somente se o alvo existir
- zero placeholders do tipo `[[X]]`, `[[slug]]`, `[[topic-name]]`

---

### 6. Atualizar `state.md` do projeto e rollup global

#### 6a. Atualizar `_knowledge/projects/{projeto}/state.md`

Ler o arquivo atual primeiro (se existir). Preservar campos não tocados pela sessão. Atualizar apenas os campos relevantes à sessão: Fase, Próximo passo, Bloqueio, PRs, Branch ativa. Se o arquivo não existir, criar com o template completo.

```markdown
---
updated: {data de hoje}
---
# State — {projeto}

**Fase:** {fase atual em 1 frase}
**Próximo passo:** {próxima ação concreta}
**Bloqueio:** {bloqueadores identificados no Step 2 — omitir linha se não houver}
**PRs:** {lista de PRs abertas — omitir linha se não houver}
**Branch ativa:** {branch feature em curso — omitir linha se não houver}
```

Somente informação sem ruído. Máximo 7 linhas de conteúdo.

#### 6b. Atualizar `_memory/current-state.md` como rollup de portfólio

Leia o arquivo atual e atualize apenas as seções afetadas:

```markdown
## Last Update: {data de hoje} ({tipo de trabalho} — {projeto})

### Projetos Ativos
| Projeto | Fase | Próximo Passo |
|---------|------|---------------|
| {projeto} | {fase curta} | {próximo passo 1 linha} |
| {outros projetos — manter linhas existentes, atualizar só o que mudou} |

### Decisions Made
{Decisões cross-project desta sessão — ou "Nenhuma decisão estratégica nesta sessão."}

### Open Questions
{Perguntas ou decisões pendentes}
```

O `current-state.md` global é rollup de portfólio — não repete detalhes que já estão no `state.md` do projeto. Próximos passos detalhados ficam no `state.md` individual.
Não manter histórico longo em `_memory/current-state.md`; se precisar preservar updates antigos, mover para `_memory/current-state-history/{YYYY-MM}.md` e deixar apenas link no rollup.

---

### 6.5 Detectar e registrar mudanças de infraestrutura

Analisar a conversa em busca de mudanças que afetam o ambiente (não apenas código):

| Tipo de mudança | Arquivo a atualizar |
|----------------|---------------------|
| Novo namespace criado | `_infrastructure/k8s/namespaces.md` |
| Nova ArgoCD app ou projeto | `_infrastructure/k8s/argocd.md` |
| Novo workload/serviço deployado | `_infrastructure/k8s/shared-services.md` ou namespace específico |
| Secret criado, rotacionado ou migrado | `_infrastructure/secrets/secrets-map.md` |
| Nova ferramenta instalada (CLI, MCP, binário) | `_infrastructure/tools/{ferramenta}.md` |
| Configuração de rede, ingress ou DNS alterada | `_infrastructure/k8s/networking.md` |
| Mudança no Vault, ESO ou ClusterSecretStore | `_infrastructure/k8s/shared-services.md` |
| Novo ambiente ou máquina configurada | `_infrastructure/environments/{host}.md` |

**Se detectou qualquer mudança de infra:**

1. Atualizar o arquivo correspondente em `_infrastructure/` com as informações novas
2. Rodar o snapshot para refletir o estado atual do cluster:
   ```bash
   bash ~/.claude/hooks/infra-snapshot.sh
   ```

**Se não houve nenhuma mudança de infra:** pular este passo silenciosamente.

---

### 7. Criar notas de decisão e aprendizado (se aplicável)

**Decisão cross-cutting** — qualifica se:
- Padroniza algo que será replicado em outro projeto (ex: padrão de commit, skill nova, protocolo de infra)
- Resolve um problema recorrente documentado no second-brain
- Modifica como agentes/skills operam (ex: nova regra no end-session, beacon criado, gate novo)

NÃO qualifica: decisão de implementação de uma única story, escolha de biblioteca específica de um projeto, fix pontual.

Se qualifica → criar `$VAULT/_decisions/{YYYY-MM-DD}-{descricao-kebab}.md`

**Gotcha ou padrão com valor cross-project:**
Criar ou atualizar `$VAULT/_learnings/{descricao-kebab}.md`

---

### 8. Verificar oportunidade de hseos brain sync

Verificar: `ls {projeto}/.hseos-output/ 2>/dev/null | head -5`

Se o diretório existir e tiver conteúdo → sugerir:
> "Há artefatos de epic em `.hseos-output/`. Execute `hseos brain sync` para copiar ADRs e learnings gerados pelo HSEOS para o vault."

Se diretório vazio ou ausente: pular silenciosamente.

---

### 8.5 Verificar candidatos a ingestão

Analisar toda a conversa em busca de conteúdo externo que ainda não foi ingerido no vault.

**Candidatos típicos:**
- URLs mencionadas (artigos, docs, specs, RFCs, posts técnicos)
- Arquivos locais referenciados mas não ingeridos (PDFs, specs, changelogs)
- Trechos de texto externo colados na conversa (release notes, ADRs de terceiros, decisões de frameworks)
- Conteúdo que foi consultado mas não registrado em `_sources/`

**Como verificar:** Para cada URL ou fonte externa mencionada na conversa, checar se existe um arquivo correspondente em `_sources/` (buscar por slug derivado do domínio ou título).

**Se houver candidatos não ingeridos:**
Listar no output e sugerir:
> "Encontrei {N} fonte(s) não ingerida(s) nesta sessão. Execute `/ingest {url_ou_fonte}` para cada uma, ou responda com 'ingerir tudo' para eu processar agora."

Se o usuário responder "ingerir tudo" (ou equivalente), executar o fluxo do `/ingest` para cada candidato em sequência antes de concluir.

### 8.6 Validar grafo depois das escritas

Se a sessão criou ou editou notas do vault, rodar:

```bash
bash $VAULT/.claude/scripts/graph-metrics.sh
```

Se `_memory/graph-metrics.md` reportar `Broken links` originados nos arquivos tocados nesta sessão, corrigir antes de encerrar. Links para conceitos ainda não canonizados devem virar texto simples ou candidatos explícitos, não WikiLinks.

**Se não houver candidatos:** omitir esta seção do output — não mencionar.

---

### 8.6 Core Drift Check (automático)

Se `_index/FEATURE-CATALOG.md` não existir: pular este passo e mencionar no output "Core Drift Check ignorado — FEATURE-CATALOG não encontrado."

Se existir, para cada implementação nova registrada no work-log desta sessão (tipo `feature`, `story`, `fix` com código novo):

1. Checar se a feature aparece no `_index/FEATURE-CATALOG.md` com `Fonte = core/*`
   - Se sim e o projeto não estava usando → registrar drift no output
2. Checar se a feature NÃO está no FEATURE-CATALOG e é domain-agnostic
   - Se sim → candidato a promoção
3. Checar se resolve algum Gap documentado em `_cores/backend-core.md` ou outro core relevante
   - Se sim → candidato de alta prioridade

**Se encontrou candidatos a promoção:**
Append em `$VAULT/_cores/promotion-backlog.md`:
```
| {YYYY-MM-DD} | {feature} | {projeto} | {N projetos estimados} | {core alvo} | sessão {tipo} | candidato |
```

**Se não encontrou candidatos:** omitir do output — silencioso.

---

### 8.6.5 Drenar fila de eventos auto-capturados

Antes da densificação, processar fila de eventos do event-broker:

```bash
bash $VAULT/.claude/scripts/event-router.sh --once
```

Em seguida, verificar `_pipeline/inbox/auto-captures-$(date).md`:

- Se há eventos pendentes, listá-los no resumo final do `/end-session` e sugerir `/review-captures` para promoção em batch
- Se a sessão atual já cobriu narrativamente os eventos (commits descritos no work-log manualmente), pode-se descartar a fila com `mv _pipeline/inbox/auto-captures-*.md _sessions/`

Reportar no output: "Auto-captures: N pendentes ({tipos detectados})".

### 8.6.6 Fechamento de entrega e validação HSEOS/distribuível

Se a sessão alterou código, scripts, comandos, skills, hooks, templates, docs operacionais, `AGENTS.md`, `CLAUDE.md`, `.specs/decisions/` ou testes, executar o fechamento técnico antes da densificação.

1. Aplicar o checklist de `/delivery-closeout`:
   - escopo entregue;
   - `git status --short` filtrando mudanças da sessão vs mudanças preexistentes;
   - validações executadas;
   - gaps aceitos ou bloqueadores.
2. Rodar validações proporcionais:
   ```bash
   bash $VAULT/tests/run-all.sh
   git diff --check -- .claude .codex _prompts tests AGENTS.md CLAUDE.md .specs
   ```
3. Se scripts shell ou Python foram tocados, validar:
   ```bash
   bash -n $VAULT/.claude/scripts/*.sh
   python3 -m py_compile $VAULT/.claude/scripts/lib/*.py
   ```
4. Se skills Codex foram alteradas, verificar paridade repo/runtime global:
   ```bash
   diff -qr $VAULT/.codex/skills /home/annonymous/.codex/skills
   ```
   Se houver drift de skill tocada nesta sessão, sincronizar a skill global ou registrar como pendência explícita.
5. Se a sessão alterou governança, hooks, regras, segurança ou postura de secrets, validar necessidade de ADR via HSEOS:
   - `governance` e `security` exigem ADR;
   - criar ou atualizar ADR em `.specs/decisions/` apenas como `Proposed`;
   - nunca marcar ADR como `Accepted` nem preencher aprovação sem revisão humana.
6. Validar contra runtime HSEOS global:
   - confirmar que o repo usa HSEOS global e não criou `.hseos` ou `.agents` local sem decisão explícita;
   - se usar `hseos-cli workflow validate`, reportar o resultado literalmente. Se o gate bloquear por baseline local `.enterprise`/`.hseos-output` ausente e o projeto estiver em modo global-runtime, registrar como limitação esperada, não mascarar como PASS.
7. Validar repositório distribuível quando arquivos operacionais foram alterados:
   - copiar o repo para diretório temporário excluindo `.git`, `.axon`, `__pycache__`, `_memory/.prompt-log.txt` e arquivos sensíveis ignorados;
   - rodar `bash tests/run-all.sh` na cópia;
   - registrar resultado e qualquer exclusão necessária.
8. Rodar scan local de padrões de secret nos arquivos tocados:
   ```bash
   rg -n "(AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9]{20,}|(?i)(api[_-]?key|secret|token|password|passwd|pwd)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{16,})" .claude .codex _prompts tests AGENTS.md CLAUDE.md .specs
   ```
   Se houver match real, bloquear o fechamento até remover ou redigir. Fixtures sintéticas devem ser construídas de modo a não parecerem credenciais reais estáticas.

### 8.7 Densificação automática do grafo (one-shot ao final)

Antes de registrar fechamento, executar (em background ou sequencial conforme preferir):

```bash
bash $VAULT/.claude/scripts/auto-linker.sh --apply --quiet \
  --scope "_knowledge/projects/{projeto}"
bash $VAULT/.claude/scripts/concept-extractor.sh
bash $VAULT/.claude/scripts/pattern-matrix-generator.sh
```

Se nenhum projeto identificado, rodar sem `--scope` é seguro (idempotente).

Output esperado:
- "[auto-linker] [APPLY] N arquivo(s) tocado(s), M link(s) novo(s)"
- "[concept-extractor] X docs, Y concepts → _index/CONCEPT-INDEX.md"
- "[matrix-gen] PATTERN-MATRIX.md / FEATURE-CATALOG.md atualizados"

Reportar no output final do `/end-session`: "Densidade: +M links, +X conceitos detectados".

Em caso de falha (auto-linker quebra), continuar — densificação é "best effort".

### 8.75 Reforço sináptico da sessão (best-effort)

Consolidar o sinal hebbiano da sessão: memórias co-ativadas (lidas/escritas/recuperadas juntas) fortalecem as sinapses entre si; co-ativações repetidas entre notas não-ligadas viram sinapses aprendidas (futuras sugestões de WikiLink no `/consolidate`).

```bash
bash .claude/scripts/sb-synapse.sh build
bash .claude/scripts/sb-synapse.sh reinforce --window 480
```

Output esperado: `[synapse] reforco: N nos co-ativados, M sinapses fortalecidas, K aprendidas`.
Reportar no output final: "Sinapses: M fortalecidas, K aprendidas". Em caso de falha, pular silenciosamente (fail-soft).

### 8.8 Sugestão preditiva para próxima sessão (opcional, best-effort)

Se projeto foi identificado no Passo 1, executar o preditor ao final:

```bash
bash $VAULT/.claude/scripts/predict.sh --project {projeto} --k 3
```

Se o script falhar por qualquer motivo (projeto sem work-log, Python ausente, etc.), pular silenciosamente.

Incluir no output final do `/end-session` a seção abaixo, com as TOP-3 predições retornadas:

```
**Sugestões automáticas para próxima sessão** (preditor — confirme antes de executar):
1. [{tipo}] {descrição} — confiança {X}%
2. [{tipo}] {descrição} — confiança {X}%
3. [{tipo}] {descrição} — confiança {X}%
```

Etiquetar claramente como "sugestões automáticas — humano confirma".
Se a saída do script for vazia ou o projeto não tiver dados suficientes, omitir esta seção.

---

### 9. Registrar no activity log e limpar flags

Append em `$VAULT/_memory/activity-log.md`:
```
## [YYYY-MM-DD] session-end | {projeto} — {tipo}: {descrição de 1 linha}
```

(HH:MM apenas se o usuário ou o sistema forneceu horário explícito na conversa — não inventar.)

Em seguida, remover os flags de sessão pendente (indicam que `/end-session` foi executado):
- Apagar `$VAULT/_memory/.needs-end-session` se existir
- Apagar `$VAULT/_memory/.compacted-without-end-session` se existir

Use a tool Bash para: `rm -f $VAULT/_memory/.needs-end-session $VAULT/_memory/.compacted-without-end-session`

---

## Output

Responda **em português (BR)** com:

### Fechamento de Sessão — {data de hoje}

**Projeto:** {nome} | **Tipo:** {tipo(s) de trabalho}

**O que fizemos:**
{Lista concisa}

**Registrado no vault:**
- work-log: `{tipo} — {descrição}` ({N} linhas)
- gotchas: {N novos} | decisions: {N novas} | learnings: {N novos}
- state.md: atualizado (fase: {fase resumida} | bloqueio: {sim — descrição / não})
- roadmap.md: atualizado / não atualizado (sessão conversacional sem entregável)
- current-state.md: atualizado
- PRs registradas: {lista ou "nenhuma nesta sessão"}
- {se auto-registro: "Projeto {nome} registrado no vault automaticamente"}

**Validações de fechamento:**
- Testes: {comandos e resultado}
- HSEOS: {PASS/BLOCKED/WARN + razão concreta}
- Distribuível: {PASS/BLOCKED/WARN + razão concreta}
- Secret scan: {sem achados / achados corrigidos / bloqueado}
- Paridade Claude/Codex: {ok / drift pendente}

**Pendências:**
{O que ficou pela metade — ou "Nenhuma pendência."}

**Próximos passos:**
{3-5 itens ordenados por prioridade}

**vault:** atualizado | pendente | nao aplicavel

{Se hseos brain sync disponível: alerta aqui}

{Se candidatos a ingestão encontrados:
**Fontes não ingeridas ({N}):**
- `{url_ou_fonte_1}` — {motivo: por que vale ingerir}
- `{url_ou_fonte_2}` — {motivo}
> Execute `/ingest {fonte}` para cada uma, ou responda "ingerir tudo" para eu processar agora.
}

---

## Regras

- Progresso de projeto vai para a pasta granular, nunca para `_knowledge/projects.md` legado
- Auto-registro cria estrutura mínima e funcional — não precisa ser perfeito, será refinado com uso
- Só criar notas cross-cutting em `_decisions/` e `_learnings/` se o conteúdo tem valor além desta sessão (ver critérios no Step 7)
- Se sessão foi improdutiva, registrar assim honestamente — sem inventar progresso
- HSEOS write rules (SKILL.md §4): respeitar strategic threshold ao escrever em `_decisions/hseos/` e `_learnings/hseos-*`
- Nunca sobrescrever `state.md` sem ler o conteúdo atual primeiro
- Não rodar `hseos install` durante `/end-session` só para satisfazer um gate; instalação/local baseline exige decisão explícita.
- Não promover ADR `Proposed` para `Accepted` nem registrar aprovação humana inferida.
- Não limpar `_memory/.prompt-log.txt`; ele é efêmero, mas só deve ser limpo após revisão explícita.
- Toda resposta final deste fluxo deve declarar exatamente um status `vault: atualizado`, `vault: pendente` ou `vault: nao aplicavel`.
