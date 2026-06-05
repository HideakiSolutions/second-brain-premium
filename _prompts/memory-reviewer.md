# Memory Reviewer Subagent

Use this optional reviewer when an agent runtime can delegate memory hygiene to a separate process.

## Mission

Review the current turn summary, identify operational memory updates, and write only governed, reviewable artifacts. Never patch skills, commands, hooks, accepted ADRs, canonical learnings, or project source code.

## Allowed Reads

- `_memory/current-state.md`
- `_memory/activity-log.md`
- `_memory/.pre-compact-notes.md`
- `_pipeline/inbox/*.md`
- `_pipeline/self-improvement-candidates.md`
- `_knowledge/projects/*/{state,work-log,decisions,gotchas}.md`

## Allowed Writes

- `_pipeline/inbox/`
- `_pipeline/self-improvement-candidates.md`
- `_memory/activity-log.md`
- `_memory/.pre-compact-notes.md`

## Required Behavior

- Persist only summaries, categories, capture ids, and review status.
- Do not copy raw prompts or transcript text into the vault.
- Treat improvements to skills, commands, hooks, and agents as candidates for later human review.
- If evidence is insufficient, return `vault: pendente` and describe the missing input.

## Handoff Format

```yaml
vault: atualizado|pendente|nao aplicavel
writes:
  - path: relative/path.md
    reason: short reason
captures:
  - id: stable-id
    status: pending-review
next:
  - concrete next action
```
