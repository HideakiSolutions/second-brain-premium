Você é o preditor de próximas tarefas do segundo cérebro. Com base no histórico de trabalho, roadmap e estado atual de um projeto, projete as 3-5 tarefas mais plausíveis para a próxima sessão.

## Argumentos

$ARGUMENTS deve conter o slug do projeto (ex: `/predict meu-projeto`).
Opcionalmente: `/predict meu-projeto --k 3` para limitar o número de predições.

Se vazio, pergunte qual projeto antes de continuar.

---

## Passos

### 1. Validar projeto

Verificar se `_knowledge/projects/{$ARGUMENTS}/` existe no vault.
Se não existir, informar quais projetos estão disponíveis e encerrar.

### 2. Executar preditor

```bash
bash $VAULT/.claude/scripts/predict.sh --project {projeto} [--k {k}]
```

Se ANTHROPIC_API_KEY estiver disponível no ambiente, o preditor usa Claude Sonnet via API para gerar as predições. Caso contrário, usa o fallback determinístico baseado em:
- Frequência histórica de tipos de tarefa (Markov leve)
- Itens pendentes do roadmap na fase atual
- Próximo passo declarado no state.md
- Open questions registradas

### 3. Apresentar resultado

Exibir a tabela de predições gerada pelo script. Em seguida, adicionar narrativa interpretativa:

**Contexto do projeto:**
Sintetize em 2-3 frases onde o projeto está agora (fase, momentum recente, bloqueadores).

**Análise das predições:**
Para cada predição (rank 1-5), explique brevemente o raciocínio por trás dela — não repita o racional mecânico do script, mas interprete no contexto do projeto.

**Sugestão de foco:**
Indique qual das predições deve ser a primeira a ser atacada e por quê. Se houver bloqueadores, sinalize.

---

## Output esperado

```
Preditor — {projeto}
Fase atual: {fase}
Fonte: llm | fallback

# Rank  Tipo       Confiança    Incerteza    Tarefa prevista
  1     task       ████████ 92% baixa        {próximo passo declarado}
  2     feature    ██████░░ 70% média-alta   {item do roadmap}
  3     fix        ████░░░░ 55% média        {correção plausível}
  ...

Detalhamento:
  [1] {descrição completa}
       Racional: {por que esta tarefa é a mais provável}
  ...

---

Narrativa:
{análise interpretativa em PT-BR}

Sugestão de foco: {tarefa #N — justificativa em 1-2 frases}
```

---

## Regras

- Não invente informações que não estão nos arquivos do projeto
- Se o work-log estiver vazio, a predição será baseada apenas em roadmap e state (menor confiança)
- Se o projeto não existir no vault, não tente executar — apenas informe
- Resultado em PT-BR
- Sugestões são indicativas — o humano confirma e prioriza
- Cache de respostas LLM é automático (1h) para evitar custo repetido por projeto
