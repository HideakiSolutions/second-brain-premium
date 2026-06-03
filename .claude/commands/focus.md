Você é o carregador de contexto cirúrgico do segundo cérebro. Carregue apenas o necessário para trabalhar no projeto informado.

## Argumentos

`$ARGUMENTS` deve conter o nome do projeto (ex: `/focus meu-projeto`).
Se vazio, pergunte qual projeto antes de continuar.

---

## Passos

### 1. Carregar contexto mínimo

Leia em sequência, parando se não encontrar o arquivo:

1. `_memory/current-state.md` — contexto geral da última sessão
2. `_knowledge/projects/{projeto}/{projeto}.md` — estado atual, stack, fase
3. `_knowledge/projects/{projeto}/gotchas.md` — manifesto enxuto de armadilhas conhecidas (se existir)
4. `_knowledge/projects/{projeto}/work-log.md` — últimas **3 entradas** apenas (se existir)

**Não leia:** MASTER-INDEX, patterns, features, outros projetos, decisions completo.
Se precisar de uma decisão específica, leia apenas o ADR mencionado no projeto.

Se `gotchas.md` apontar para arquivos em `_knowledge/projects/{projeto}/gotchas/`, leia no máximo 5 entradas detalhadas relevantes para a tarefa atual. Nunca carregar o diretório inteiro.
Se precisar de decisões locais, leia primeiro `decisions.md` como manifesto e depois no máximo 3 entradas específicas em `_knowledge/projects/{projeto}/decisions/`.

### 2. Verificar pendências do projeto

Se existir `_knowledge/projects/{projeto}/roadmap.md`, leia a fase atual.
Se existir `_memory/heartbeat-latest.md` com alertas relacionados ao projeto, note-os.

### 2.5 Retrieval semântico (se infra disponível)

Verificar se Qdrant está online via `bash .claude/scripts/sb-reindex.sh status` (silencioso, ignorar se falhar).

Se online, rodar duas buscas leves:
```bash
bash .claude/scripts/sb-search.sh "{projeto} próximo passo bloqueios" --project {projeto} --k 3
bash .claude/scripts/sb-search.sh "decisão recente {projeto}" --kind decisions --project {projeto} --k 3
```

Use os resultados para enriquecer a seção "Decisões/learnings relevantes" do briefing — apenas se houver match com score >0.5.

Se sb-search não estiver disponível, omitir esta seção. Nunca falhar o /focus por falta de Qdrant.

### 3. Montar briefing focado

Com base no que foi lido, responda em português (BR):

---

## Output

### Foco: {projeto}

**Fase:** {fase atual do projeto}
**Última sessão:** {data da última entrada no work-log, se disponível}

**Contexto:**
{2-3 frases descrevendo onde o projeto está agora — sem repetir o que está nos arquivos, sintetize}

**Próximo passo:**
{O item mais importante e acionável agora — 1 linha, direto}

**Gotchas ativos:**
{Lista curta dos gotchas mais relevantes para o trabalho atual, ou "Nenhum registrado."}

**Pendências:**
{O que ficou pela metade na última sessão, extraído do current-state ou work-log, ou "Nenhuma."}

---

> Contexto carregado. Pode começar.

---

## Regras

- Se o projeto não existir em `_knowledge/projects/`, informe e ofereça criar a estrutura mínima
- Não invente informações que não estão nos arquivos
- Mantenha o output curto — este comando é uma aterrissagem, não um briefing completo
- Se quiser o portfólio completo, use `/daily-briefing`
