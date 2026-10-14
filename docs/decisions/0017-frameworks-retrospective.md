# 0017 — Frameworks retrospective: what LangGraph, the OpenAI Agents SDK, or DeepSeek Harness would have given and cost

- **Date:** 2026-10-14
- **Status:** Accepted
- **Relates to:** [0008](0008-hybrid-workflow-over-agentic.md), [0009](0009-durable-execution-with-step-checkpoints.md), [0010](0010-bounded-proposal-only-resolver.md), [0011](0011-human-gate-before-sending.md), [0015](0015-hybrid-over-autonomous-measured.md)

## Context

PawDesk's agent machinery was built by hand on the official `openai` client:
- the durable orchestrator;
- the resolver's tool loop;
- the human gate;
- tracing;
- retries;
- recorded responses.

Hand-building was deliberate, to keep every stop condition, checkpoint, and trace visible and testable. Now that it exists, the question is what an agent framework would have provided, and at what price.

The parts a framework would replace, measured as non-blank, non-comment lines (docstrings included):

| Part | Lines |
|---|---|
| Orchestrator: steps, checkpoints, resume, failure, routing (`app/orchestrator.py`) | 538 |
| Resolver: eligibility, tools, loop, verification (`app/resolver.py`) | 407 (the loop itself, about 46) |
| Model client: retries, deadlines, cost, tool calls (`app/llm.py`) | 248 |
| Tracing (`app/tracing.py`) | 127 |
| Lifecycle guard and transitions (`app/lifecycle.py`, `app/transitions.py`) | 105 |
| Staff decisions (`app/approvals.py`) | 85 |

The comparison below rests on each framework's documentation and published descriptions, not on porting PawDesk to it. No framework code was written for this record.

## Options considered

### LangGraph (graph workflows with persistence)
- **Would give:**
  - a `StateGraph` for the fixed order of steps;
  - a checkpointer that saves state after every step and resumes a thread after a crash;
  - `interrupt()` to pause for a person, and a resume command to continue, which is exactly the shape of `needs_review`;
  - streaming, and "time travel" (replaying or forking from earlier checkpoints).
- **Overlap with PawDesk:** most of the orchestrator's resume and failure plumbing, and the mechanics of the human gate.
- **Would cost:**
  - **Checkpoints would be framework state, kept apart from the business data.** PawDesk saves each step's result in the same transaction as the request's state change and its transition log row, guarded by the lifecycle rules and a version check (0009). A framework checkpoint lives outside that transaction unless the two are carefully joined, and the domain's own guard would still be needed.
  - The checkpoints would be serialized graph state rather than queryable rows. The dashboard and the build walkthrough read PawDesk's step results directly.
  - There would be another abstraction to learn and upgrade.
- **Fit:** the strongest candidate if PawDesk grew into many workflows, long waits, or several workers.

### OpenAI Agents SDK (agents, tools, handoffs, guardrails)
- **Would give:**
  - a runner for the tool loop with a turn limit;
  - function tools with schemas from type hints;
  - handoffs between agents;
  - input and output guardrails that can stop a run;
  - session memory;
  - built-in tracing of model calls, tool calls, handoffs, and guardrails.

  It's provider-agnostic, so it would work with the model PawDesk uses through OpenRouter.
- **Overlap with PawDesk:** the resolver's loop (about 46 lines), its tool schemas, and part of the tracing.
- **Would cost:**
  - PawDesk's stuck guard (stop on any repeat of an earlier call) and the "proposals are re-checked by code" step would still be custom.
  - Tracing would have to be pointed at PawDesk's own spans. The dashboard depends on exact provider-reported cost, per-attempt retry records, and spans stored in Postgres, which built-in tracing doesn't give by default.
  - Retry ownership would need care, so the SDK and PawDesk's own client don't both retry.
  - Its multi-agent strengths (handoffs) answer a question PawDesk measured and declined (0008, 0015).
- **Fit:** a reasonable replacement for the resolver loop alone. It shrinks little of what matters most here.

### DeepSeek Harness (open-source agent runtime)
- **Would give:** a plugin-based runtime. Per its published descriptions, models, tools, skills, sandboxes, storage, loops, scheduling, and the UI are all swappable plugins, with preset work modes centered on a general coding agent.
- **Overlap with PawDesk:** little. It's built for open-ended agents that act (files, shells, sub-agents). PawDesk deliberately keeps its one agent proposal-only, with read-only tools.
- **Would cost:**
  - a runtime far larger than the problem;
  - a developer-preview status, with breaking changes possible, according to the reviews available;
  - a design center (autonomy) that runs against the measured result in 0015.
- **Fit:** not a fit for a business workflow with a human gate. It might fit internal developer tooling around the project.

## Decision

**Keep the hand-built implementation for PawDesk as it stands.**
- **The reason:** the parts that make PawDesk safe are domain rules no framework provides. The framework would supply plumbing around them:
  - the lifecycle guard;
  - step results committed with state changes;
  - code-decided eligibility and routing;
  - re-verified proposals;
  - the promise check;
  - a human gate as a database state.
- **Writing the plumbing by hand** (about 1,500 lines, all tested and traced to specs) made every stop condition and checkpoint explicit and testable.

**If PawDesk grows, adopt in this order:**
1. **LangGraph** for the workflow, once there are several workflows, long waits, or many workers. Keep step results and the lifecycle guard in the business database, and treat the framework checkpoint as an implementation detail.
2. **The OpenAI Agents SDK** for agent loops, once an agent needs many tools or handoffs. Route its tracing into PawDesk's spans.

## Consequences

- **Good:** No framework lock-in or upgrade churn, and the tracing, durability, and approval rules stay exactly as specified and tested.
- **Cost:** PawDesk maintains code a framework would maintain for it: retries, the resume loop, and the human-gate plumbing. It also lacks framework conveniences, like time-travel debugging and built-in streaming of agent steps.
- **Cost:** This retrospective rests on documentation, not a port. A spike porting the resolver loop to the Agents SDK, and the orchestrator to LangGraph with a Postgres checkpointer, would turn it into a measurement. That's the next step if either adoption trigger above is reached.

## Sources

- LangGraph human-in-the-loop and interrupts: https://docs.langchain.com/oss/python/langgraph/human-in-the-loop
- OpenAI Agents SDK (package and overview): https://pypi.org/p/openai-agents
- DeepSeek Harness overviews (third-party; maturity claims differ between them):
  - https://www.datacamp.com/tutorial/deepseek-harness
  - https://nexforce.ai/en/blog/deepseek-harness-framework-agentes
  - https://pandaily.com/deepseek-harness-hands-on-four-modes-model-plus-harness-equals-agent-aug2026
