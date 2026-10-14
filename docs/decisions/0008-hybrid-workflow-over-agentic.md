# 0008 — A hybrid workflow: code decides the order, models only read

- **Date:** 2026-10-14
- **Status:** Accepted

## Context

A booking request passes through reading (the free-text message and the certificate image), checks (vaccine compliance, kennel capacity, pet identity), and routing (draft a reply, or resolve problems first). Only the reading needs a language model. Every check has a correct answer that code can compute and test.

The common agent architectures put a model in charge of more or less of this:

| Pattern | Who decides what happens next |
|---|---|
| Prompt chaining | Code, in a fixed order |
| Routing | Code or a classifier picks one of several fixed paths |
| Parallelization (sectioning or voting) | Code fans out independent work and gathers it |
| Orchestrator–workers | A model plans subtasks at runtime and hands them to workers |
| Evaluator–optimizer | A model critiques and revises its own output in a loop |
| Autonomous agent | A model with tools picks every next action |
| Multi-agent (supervisor, peer handoff, shared blackboard) | Several models coordinate, through a manager, direct handoffs, or a shared workspace |

Errors compound across model decisions. If each decision is right 95% of the time, a chain of five is right about 77% of the time (0.95⁵). Each decision handed to a model also needs its own evaluation, trace, and defense against prompt injection, because pet-parent messages and images are untrusted.

## Options considered

1. **Fully agentic.** One agent with tools for intake, records, compliance, capacity, and routing, choosing the order itself. Flexible, but its path can't be predicted from the data. An injected instruction can steer it, and every run needs a model decision just to reach the deterministic checks.
2. **Multi-agent supervisor.** A manager agent delegates to intake, records, and checking agents. This adds coordination calls and a second layer where errors compound, for a flow that never changes shape.
3. **LLM-planned orchestrator–workers.** A model writes the plan per request. That fits when the subtasks can't be known in advance, which isn't the case here.
4. **Hybrid workflow.** A plain async function fixes the order: concurrent reading (sectioning), then deterministic checks, then code routing with listed reasons. Models are used only where the input is messy. A narrowly scoped agent is allowed later, inside a fenced step, where the work really is open-ended (the resolver).

## Decision

Option 4.

- `app/orchestrator.py` branches only on the request's lifecycle state and saved step results.
- Model calls happen only inside the intake and records steps. Their outputs are validated, and they can raise issues but never approve anything.
- Compliance, capacity, pet-name matching, and routing are plain code with unit tests. Routing records every reason a request needs a closer look.

## Consequences

- **Good:** The path of every request can be predicted from its data, and tested without a model.
- **Good:** Prompt injection can at most add an issue, which routes the request toward a person. It can't skip a check.
- **Good:** Two model calls per request, made at the same time, so cost and latency stay small and bounded.
- **Cost:** New kinds of work need code changes, not just a prompt change.
- **Cost:** The workflow can't improvise. Unusual requests end up in `resolving` and, later, with a person. For a booking desk, that's intended.
- **Follow-up:** Parallel *voting* (two independent reads of a certificate, with disagreement sent to review) fits this structure without changing it. The records evaluation showed confident misreads of handwritten dates that a single read can't catch.
