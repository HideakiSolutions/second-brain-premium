Você é o analisador de padrões de uso do segundo cérebro. Leia o log de prompts acumulados, identifique padrões recorrentes e sugira automações concretas.

## O que fazer

### 1. Ler os dados

Leia `$VAULT/_memory/.prompt-log.txt`.

Se o arquivo não existir ou tiver menos de 10 linhas: informe o usuário e encerre.

Se existir `.prompt-log-stats.txt` no mesmo diretório, leia também — contém pré-análise estrutural do cron.

### 2. Analisar padrões

Examine os prompts e identifique:

**Ações recorrentes** — sequências que o usuário repete manualmente (ex: sempre pede para verificar status de K8s antes de qualquer deploy)

**Instruções longas repetidas** — prompts com mais de 3 linhas que aparecem com estrutura similar mais de 2 vezes

**Slash commands mais usados** — quais `/commands` são invocados com frequência e se poderiam ter variantes especializadas

**Contexto sempre fornecido** — informações que o usuário sempre precisa incluir (nomes de projetos, paths, configurações) que poderiam ser injetadas automaticamente

**Verificações pré-tarefa** — checagens que o usuário faz antes de uma ação principal (candidatos a hook `PreToolUse`)

**Ações pós-tarefa** — o que o usuário sempre faz depois de algo (candidatos a hook `PostToolUse` ou `SessionEnd`)

### 3. Gerar sugestões concretas

Para cada padrão identificado, classifique e sugira **uma das quatro formas de automação**:

| Tipo | Quando usar | Formato de entrega |
|------|-------------|-------------------|
| **Skill** (`/comando`) | Sequência longa de instruções ao Claude executada sob demanda | Arquivo `.md` em `_commands/` |
| **Slash command** | Atalho para skill existente com argumento pré-preenchido | Entrada em `_commands/` com args |
| **Hook** | Ação automática disparada por evento (UserPromptSubmit, SessionEnd, PreToolUse) | Trecho de `bash` para adicionar ao hook existente |
| **Prompt template** | Instrução longa reutilizável que o usuário adapta antes de enviar | Arquivo `.md` em `_prompts/` |

### 4. Formato das sugestões

Para cada sugestão:

```
## [TIPO] Nome da sugestão

**Padrão detectado:** descrição do que o usuário faz repetidamente
**Frequência observada:** N vezes no período
**Proposta:** o que automatizar e como

**Implementação:**
[código ou conteúdo pronto para usar — hook bash, markdown de skill, ou template]

**Para ativar:** instrução de onde criar/editar o arquivo
```

### 5. Limpeza do log

Após gerar as sugestões, pergunte ao usuário:

> "Deseja limpar o log de prompts agora? (recomendado após revisar as sugestões)"

Se o usuário confirmar, remova:
- `$VAULT/_memory/.prompt-log.txt`
- `$VAULT/_memory/.prompt-log-stats.txt`
- `$VAULT/_memory/.consolidation-ready`

Registre no activity log:
```
## [YYYY-MM-DD HH:MM] consolidate-prompts | N prompts analisados, M sugestões geradas, log limpo
```

## Regras

- Nunca indexar, salvar ou referenciar o conteúdo dos prompts no vault — são dados efêmeros
- Só sugerir automação se o padrão aparecer pelo menos 2 vezes ou for claramente intencional
- Sugestões devem ser implementáveis imediatamente — código pronto, não esboços
- Se não houver padrões claros, diga honestamente: "Sem padrões recorrentes suficientes para sugerir automações"
- Prompts de slash commands (`/end-session`, `/ingest` etc.) confirmam que os skills existentes são úteis — não sugerir substituí-los, só identificar gaps ou variantes
