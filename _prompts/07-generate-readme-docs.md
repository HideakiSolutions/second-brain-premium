# 07 — Gerar README e Documentação de Projeto

Use este prompt para gerar ou atualizar o README.md e a documentação do vault de qualquer projeto.
Substitua `{PROJETO}` pelo slug real antes de colar.

---

Gere a documentação completa do projeto `{PROJETO}` seguindo dois destinos:

## Destino 1 — README.md do repositório

Atualize ou crie `<projects-root>/{PROJETO}/README.md` com as seguintes seções, nesta ordem:

### Estrutura obrigatória do README

```markdown
# {PROJETO} — {Tagline em 1 frase}

> {Subtítulo explicando o problema resolvido e a abordagem}

## Como funciona

{Diagrama ASCII ou prose de 3-5 linhas mostrando o fluxo principal}

## Stack Técnico

| Componente | Tecnologia |
|------------|-----------|
| ...        | ...       |

## Instalação / Build

{Pré-requisitos mínimos + comandos para build/install}
{Se houver constraints de ambiente (ex: -j2), documentar aqui com o motivo}

## Uso

{Comandos CLI principais com exemplos reais}

## API / Ferramentas expostas

{Se MCP: tabela com Tool | Parâmetros | Descrição}
{Se REST: tabela com Método | Endpoint | Descrição}
{Se lib: exemplos de uso das funções principais}

## Configuração

{Arquivo de config, variáveis de ambiente, exemplos mínimos}

## Arquitetura interna

{Árvore de diretórios src/ com 1 linha por módulo}
{Diagrama de fluxo de dados se pertinente}

## Roadmap

{Lista de features planejadas — SOMENTE o que ainda NÃO está implementado}
{Remova qualquer item que já foi entregue}
```

**Regras para o README:**
- Não invente nada — leia o código/vault antes de escrever
- O Roadmap deve refletir o estado ATUAL: remova itens entregues, adicione os pendentes reais
- Se há métricas reais (token reduction, benchmarks), inclua-as
- Não adicione seções de "Contributing" ou "License" a menos que já existam
- Máximo 250 linhas — se passar, corte prosa, mantenha tabelas

## Destino 2 — vault do segundo cérebro

Atualize os seguintes arquivos em `$VAULT/_knowledge/projects/{PROJETO}/`:

### `{PROJETO}.md` (ou `index.md` se usar second-brain-starter)

```yaml
---
tags: [wiki, project, {categoria}]
status: active
created: {data-original}
updated: {hoje}
---
```

Seções: What It Is (2-3 frases), Quick Stats (tabela), Key Features (lista), How to Run (comandos), Deep Dive (links para outros arquivos).

**Quick Stats deve refletir o estado atual:** número real de linguagens, tools, serviços, etc.

### `modules.md`

Atualizar tabela de módulos/serviços com responsabilidades atuais.

### `roadmap.md`

Sincronizar com o Roadmap do README: mesmas features, mesmo status. Adicionar seção "Entregues nesta sessão" com o que foi implementado recentemente.

## Fluxo de execução

1. Ler `_knowledge/projects/{PROJETO}/{PROJETO}.md` para entender o estado atual do vault
2. Ler o README.md existente do repositório
3. Ler `roadmap.md` do vault
4. Consultar `work-log.md` para saber o que foi implementado recentemente
5. Identificar gaps entre vault ↔ README ↔ código real
6. Atualizar README.md primeiro
7. Atualizar os arquivos do vault
8. Reportar o que mudou em cada destino

## Output esperado

```
### Documentação atualizada — {PROJETO}

**README.md:**
- {O que foi adicionado/removido/corrigido}

**Vault:**
- {PROJETO}.md: {o que mudou}
- roadmap.md: {features removidas do backlog + novas adicionadas}
- modules.md: {módulos novos ou atualizados}

**Gaps encontrados:**
- {Discrepância entre vault e código, se houver}
```
