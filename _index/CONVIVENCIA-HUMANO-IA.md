---
tags: [index, navigation, knowledge-mgmt, active]
status: active
created: 2026-07-08
updated: 2026-07-08
---

# 🤝 Convivência Humano ↔ IA

> Contrato que mantém as duas otimizações do vault em harmonia: navegável e bonito para o humano no Obsidian, atômico e machine-parseable para os agentes.

## O princípio

O vault tem **duas superfícies sobre os mesmos arquivos**:

| Superfície | Para quem | Otimiza | Exemplos |
|---|---|---|---|
| **Navegação** | humano no Obsidian | escaneabilidade, beleza, orientação | [[../HOME\|HOME]], MOCs (`README.md` por pasta), índices, Graph View |
| **Canônica** | agentes via recall/busca/injeção | atomicidade, metadados, links resolvíveis | notas de `_decisions/`, `_learnings/`, `_patterns/`, `_features/`, projetos |

Não são camadas rivais: **todo wikilink de navegação é também uma sinapse** - o mapa que orienta o humano densifica o grafo que a IA percorre.

## Regras da camada de NAVEGAÇÃO (humano primeiro)

1. **Emoji é bem-vindo** em títulos H1 e tabelas de MOCs/dashboard. Paleta estável por camada: 🧠 home · 📇 índices · 🏗️ projetos · 📐 patterns · 🧩 features · ⚖️ decisions · 🎓 learnings · 🧱 cores · 🛰️ infra · 📰 conteúdo · 📥 fontes · 🕰️ memória.
2. **Callouts do Obsidian** (`> [!tip]`, `> [!warning]`, `> [!info]`) são encorajados - renderizam para humanos e degradam como blockquote legível para IA.
3. Todo MOC linka [[../HOME|HOME]] e os vizinhos - a navegação nunca tem beco sem saída.
4. MOCs respondem "o que vive aqui, como entrar, que pergunta este lugar responde" em menos de ~45 linhas.

## Regras da camada CANÔNICA (IA primeiro)

1. **Emoji NUNCA em nomes de arquivo, slugs, tags ou frontmatter** - quebram resolução de link, âncoras e parsing.
2. Frontmatter obrigatório e taxonômico: camada + maturidade; notas atômicas (alvo: ~1KB de mediana).
3. Conteúdo canônico não vira "arte visual": prosa direta, tabelas com dados, links com contexto. Beleza aqui é clareza.
4. Emoji pontual DENTRO de nota canônica é tolerado quando carrega significado (ex.: ✅/⚠️ em tabelas de status), nunca decorativo em massa.

## Sincronia (como uma camada alimenta a outra)

- MOCs e HOME são **notas indexadas normalmente**: entram no Qdrant, no grafo sináptico e no recall - a IA usa o mapa humano como atalho de navegação.
- O Graph View humano e o grafo sináptico da IA são projeções da MESMA malha de links; cores por pasta ≈ `kind` do retrieval.
- Quando o `/consolidate` propuser links LEARNED (co-ativação repetida), a curadoria humana decide olhando o grafo - o uso da IA sugere, o humano oficializa.
- Manutenção dos MOCs: quem cria pasta/camada nova cria o `README.md` dela na mesma sessão.

## Anti-padrões (o que quebraria a harmonia)

- Renomear arquivos para "ficar bonito" (quebra slugs, links e memória dos agentes)
- Duplicar conteúdo canônico dentro de dashboards (dashboards LINKAM, não copiam)
- Plugins do Obsidian que reescrevem notas automaticamente sem passar pelos hooks
- Emoji em tags ou frontmatter "para dar cor" (o Graph View já colore por pasta)

## Related

- [[../HOME|HOME]] · [[README|MOC Índices]]
- [[../_decisions/2026-07-08-camada-sinaptica-memoria-associativa|ADR Camada Sináptica]]
