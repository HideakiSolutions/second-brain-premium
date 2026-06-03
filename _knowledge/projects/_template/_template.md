---
tags: [project-index, wiki, project, {{DOMAIN}}]
status: active
created: {{YYYY-MM-DD}}
---

# {{Project Name}}

## What It Is
{{Frase única descrevendo o problema que o projeto resolve, quem usa, e por que existe. Evite jargão de marketing — vai direto ao domínio.}}

## Quick Stats
- Stack: {{linguagens, frameworks principais, runtimes}}
- Services: {{N bounded contexts | N módulos | N pacotes — descrever a granularidade real}}
- Phase: {{Fase X — descrição curta, ex: "Fase 2 — POC" ou "MVP em produção"}}
- Patterns: [[../../../_patterns/{{pattern-slug}}|{{Pattern Name}}]] · [[../../../_patterns/{{pattern-slug-2}}|{{Pattern Name 2}}]]

## Key Reusable Features
→ [[../../../_features/{{feature-slug}}|{{Feature Name}}]] — {{status: production | poc | adopted}}
→ [[../../../_features/{{feature-slug-2}}|{{Feature Name 2}}]] — {{status}}

## How to Run
```bash
cd <projects-root>/{{repo-name}}
{{comando de bootstrap, ex: docker-compose up -d, dotnet run --project src/Gateway, npm start}}
```

## Deep Dive
→ [[modules]] · [[integrations]] · [[gotchas]] · [[decisions]] · [[roadmap]]
