# ADR-0001 — Assisted-First Core Workflow Automation

**Status:** Proposed
**Date:** 2026-05-24
**Authors:** Codex agent
**Approved by:** —
**Affects Standards:** HSEOS ADR Compliance AD-04, AD-08; second-brain AGENTS.md workflow map; Claude/Codex runtime parity
**Supersedes:** N/A
**Superseded By:** N/A

---

## Context

The second-brain runtime had repeated manual prompts around development workflow closeout: completion audit, validation, deployment checks, product UX checks, PR/merge/tag recording, and self-improvement candidate review.

The requested package adds Claude commands, Codex skills, prompt templates, assisted hooks, and `learn-loop` sanitization. This affects governance and security posture because hooks now suggest validation tiers, record assisted PR/merge/tag captures, and block likely secret writes in sensitive text targets.

HSEOS ADR Compliance requires an ADR for security posture changes and governance or standards modifications.

## Decision

We will adopt an assisted-first core workflow automation package for the second-brain runtime.

The package will:

- expose canonical commands for completion audit, delivery closeout, live deploy validation, UX product audit, and skill evolution;
- maintain Claude/Codex parity through repository-local Codex skills and global runtime synchronization;
- keep hooks advisory by default, except for blocking likely secret writes in sensitive markdown, prompt, rule, log, JSON, YAML, or env targets;
- keep raw prompt logs ephemeral in `_memory/.prompt-log.txt` and analyze only sanitized aggregate signals;
- write new PR/merge/tag/release detections to `_pipeline/inbox/` for human review, not directly to durable vault notes;
- require human review before durable changes to skills, rules, hooks, secrets, or accepted decisions.

## Alternatives Considered

### Option A — Keep the workflow fully manual

- **Description:** Continue relying on ad hoc prompts and manual closeout.
- **Pros:** No new hooks, no governance change, no additional tests.
- **Cons:** Repeated prompts, inconsistent validation, weak capture of merge/release events, higher chance of declaring incomplete work done.
- **Rejected because:** The observed workflow needs repeatable validation and closeout without removing human control.

### Option B — Fully autonomous workflow automation

- **Description:** Let hooks apply changes to skills, rules, decisions, and vault notes automatically.
- **Pros:** Maximum automation and lower manual overhead.
- **Cons:** Violates assisted-first control, increases risk of unreviewed governance drift, and can persist bad inferences from prompt logs.
- **Rejected because:** Durable procedural and governance changes require review.

### Option C — Assisted-first automation

- **Description:** Hooks suggest, classify, sanitize, and enqueue; humans approve durable changes.
- **Pros:** Reduces repetitive prompting while preserving review gates and auditability.
- **Cons:** Still requires manual review of candidates and captures.
- **Selected because:** It matches HSEOS governance constraints and the second-brain control model.

## Consequences

### Positive

- Standardizes the development cycle from focus through closeout.
- Reduces raw prompt leakage by moving analysis to sanitized categories.
- Adds a secret guard for sensitive text writes.
- Preserves human approval for durable governance and vault changes.
- Improves Claude/Codex parity through explicit repository-local skills.

### Negative / Trade-offs

- Adds more local scripts and tests to maintain.
- Claude hooks and Codex skills remain different runtime surfaces; parity depends on tests and synchronization.
- Secret detection is pattern-based and can produce false positives or miss unknown formats.
- Runtime-global synchronization is still a copy step, not a package installer.

### Risks & Mitigations

- **Risk:** Hook behavior blocks normal work. **Mitigation:** hooks are advisory except secret write blocking; tests cover benign placeholder fixtures.
- **Risk:** Prompt text leaks into durable outputs. **Mitigation:** `PromptLogSanitizer` emits categories, and `learn-loop` reads sanitized temporary output.
- **Risk:** Repo and global Codex runtime drift. **Mitigation:** repository parity tests plus explicit global sync after changes.
- **Risk:** Captures become unreviewed facts. **Mitigation:** `PostMergeRecorder` writes only to `_pipeline/inbox/` with `pendente-revisao`.

## Affected Standards

| Standard | Section / Rule | Change |
|---|---|---|
| HSEOS ADR Compliance | AD-04 | Documents the security posture change introduced by SecretLeakGuard. |
| HSEOS ADR Compliance | AD-08 | Documents the governance/workflow change introduced by assisted hooks and canonical commands. |
| second-brain `AGENTS.md` | Paridade Claude/Codex | Extends workflow map with new commands and skills. |
| second-brain `AGENTS.md` | Fluxo Padrao De Desenvolvimento | Defines the recommended assisted development cycle. |

## Compliance

- [ ] Approved by Engineering Leadership
- [ ] Approved by Security Owner
- [x] Repository tests cover commands, Codex parity, secret guard, assisted hooks, and sanitized learn-loop
- [x] Raw prompt log remains ephemeral and is not copied into this ADR
- [x] Captures are routed to `_pipeline/inbox/` for review
- [ ] Activation date: pending approval
- [ ] Review date: 2026-06-24
