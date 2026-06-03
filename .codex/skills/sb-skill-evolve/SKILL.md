---
name: sb-skill-evolve
description: "Consuma candidatos do learn-loop e gere patch plan revisavel para skills, comandos, hooks, templates ou config, sem aplicar automaticamente."
license: Apache-2.0
metadata:
  owner: second-brain
  vault: "$VAULT"
  vault_name: "Second Brain"
  vault_prefix: "sb"
  source_command: ".claude/commands/skill-evolve.md"
---

# Second Brain Skill Evolve

Use quando `_pipeline/self-improvement-candidates.md` tiver propostas aceitas ou quando o usuario pedir evolucao do workflow.

## Workflow

1. Leia `_pipeline/self-improvement-candidates.md`.
2. Verifique evidencia agregada e remova ruido de tool output, compactacao, stdout local e prompts de agente.
3. Classifique por frequencia, risco, tipo e paridade Claude/Codex.
4. Para candidatos viaveis, gere patch plan com arquivos, validacoes e rollback.
5. Marque candidatos fracos como `aguardar-dados`.

## Regras

- Nao aplique patches durante esta skill.
- Nao copie prompts brutos para notas permanentes.
- Nao crie automacao destrutiva ou autoaplicada.
- Mudancas em skills, comandos, hooks, secrets e decisoes exigem revisao humana.
- Toda implementacao futura deve validar paridade Claude/Codex e rodar `tests/run-all.sh`.
