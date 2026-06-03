# ADR-0002 - Agentic Memory Contract For Second-Brain Usage

**Status:** Proposed
**Date:** 2026-05-31
**Authors:** Codex agent
**Approved by:** -
**Affects Standards:** second-brain AGENTS.md; Claude/Codex runtime parity; assisted agent workflow
**Supersedes:** N/A
**Superseded By:** N/A

---

## Context

The second-brain already provides commands, Codex skills, hooks, semantic search,
graph tooling, event capture, and structured vault destinations. The remaining
gap is behavioral: agentic development still depends on each agent remembering
to consult and update the vault manually.

This creates failure modes:

- agents ask the human for decisions before checking prior ADRs, learnings, or
  project state;
- plans, blockers, findings, and next steps stay only in chat context;
- Claude hooks capture some events, but Codex, Antigravity, and other runtimes
  may not run equivalent closeout flows;
- repeated decisions and duplicated notes can appear because precedent search is
  optional in practice.

This is a governance change because it modifies the required operating contract
for agents.

## Decision

We will make the second-brain memory workflow an explicit agent contract in
`$VAULT/AGENTS.md`.

Any agent operating on this repo or on mapped projects must:

- load minimum context from the second-brain before productive work;
- consult semantic search, project state, decisions, and precedents before
  asking the human for a decision;
- register plans, activity, blockers, findings, decisions, and next steps in the
  canonical vault locations;
- run `/delivery-closeout` for verifiable deliveries and `/end-session` for any
  productive session, or execute equivalent script/manual steps when slash
  commands are unavailable;
- ingest relevant external sources used as durable support;
- treat auto-captures as pending review until promoted;
- avoid duplicate ADRs, learnings, gotchas, and patterns by searching for
  precedents first;
- keep secrets and raw prompts out of durable vault notes.

The contract remains assisted-first. Agents may prepare, classify, write drafts,
and update structured notes, but acceptance of governance changes and destructive
or external actions remains human-controlled.

## Alternatives Considered

### Keep memory discipline as guidance

This keeps the current model, where commands exist but agents decide when to use
them. It is simple, but it does not solve the actual gap: inconsistent behavior
across runtimes.

### Make hooks fully automatic

This would reduce manual work for Claude sessions, but it does not cover all
agent runtimes and increases the risk of unreviewed durable writes.

### Define an agent contract

This makes the expected behavior portable across Claude, Codex, Antigravity, and
future agents. Hooks and skills can still automate pieces of the workflow, but
the obligation exists even when the runtime has no native hook support.

This option is selected.

## Consequences

Positive:

- decisions are checked against existing memory before escalating to the human;
- plans, pending work, findings, and closeout state become durable;
- Codex and other agents have the same responsibility as Claude sessions;
- future automation can target a clear contract instead of implicit behavior.

Negative:

- agents must spend extra time on lookup and closeout;
- the vault may receive more frequent updates and needs graph hygiene;
- bad implementation of the contract could create noisy notes if agents do not
  summarize carefully.

## Validation

Validation for this ADR is procedural:

- `AGENTS.md` contains the explicit contract;
- HSEOS ADR validation marks governance changes as ADR-required;
- future changes to commands, skills, hooks, or rules must preserve
  Claude/Codex parity and run the second-brain test suite when implementation
  files are changed.
