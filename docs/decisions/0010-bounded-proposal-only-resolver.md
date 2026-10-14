# 0010 — The resolver is a bounded, proposal-only agent with a hand-written loop

- **Date:** 2026-10-14
- **Status:** Accepted

## Context

Some booking requests can't go ahead as asked: no kennel of the pet's size is free for those nights, or a required vaccine won't cover the stay. A helpful desk offers alternatives: other dates, a larger kennel, or an updated vaccine record. PawDesk is a hybrid workflow where code decides and models read (decision record 0008). Finding alternatives is the one place where an agent (a model calling tools in a loop) is worth considering, because the fixes interact. Dates that free a kennel can push the stay past a vaccine's expiry, a larger kennel helps only with capacity, and an updated record helps only with coverage.

An agent is also the least predictable pattern. Each model decision compounds error, a loop can run without making progress, and a model that can act can be steered by text it reads.

## Options considered

1. **No agent.** A deterministic search lists free windows and failing vaccines, and staff combine them. It is fully predictable, and it covers the common single-problem case. It can't weigh combinations or explain a recommendation.
2. **A free agent.** The model gets the customer message and broad tools (search, reserve, message the customer). It is flexible, but the injection surface is large, it can act on its own, and its outcomes are hard to test.
3. **A bounded, proposal-only agent.** The model gets only structured facts and read-only tools bound to the request. Its only exit is a proposal that code re-checks, and it stops on hard limits.
4. **An agent framework** (a graph or agent SDK) to run the loop. It brings built-in loops, memory, and tracing, but those hide the parts this project needs to show and test: the stop conditions, the stuck guard, and what goes into each turn.

## Decision

Option 3, with a hand-written loop (not option 4).

- **Code decides whether the agent runs.** Only capacity and vaccine-coverage problems reach it. An unknown pet, a records problem, suspected injection, or an unknown expiry goes to a person with no model call.
- **No untrusted text.** The prompt is built from typed values only. The customer's message, notes, certificate text, and even the pet's name as written are excluded. This removes the injection surface instead of defending it.
- **Read-only tools bound to the request.** The pet, facility, service, and dates are fixed in code, so the model can choose only a search range, dates, or a size class. Mistakes come back as error results the model can read.
- **Stop conditions:**
  - a valid proposal;
  - any repeat of an earlier tool call with the same arguments (tools are deterministic within a run, so a repeat can't make progress);
  - an answer without a tool call;
  - 6 model calls or 12 tool calls.
- **Proposals, not actions.** Every option is re-checked against capacity and compliance and stored as verified or not. The lifecycle allows only `resolving → drafting`, so nothing the agent produces can approve a booking. A person reviews every request that passed through `resolving`.
- **The loop is plain Python** (one function of a few dozen lines) over the traced model client, with one `llm` span per turn and one `tool` span per call.

## Consequences

- **Good:** The agent's worst case is a useless proposal or an escalation, never a wrong action. Both end in front of a person.
- **Good:** Every boundary is testable without a model: eligibility, tools, stop conditions, and verification run against scripted turns.
- **Good:** Cost is bounded: at most 6 model calls per blocked request, and none for problems the agent can't fix.
- **Cost:** For a single problem, a deterministic search would usually find the same option. The agent has to earn its place on interacting problems and in the staff summary. This is worth measuring before the agent grows.
- **Cost:** A hand-written loop has no built-in features such as memory, streaming, or human-in-the-loop pauses. These are added only when needed.
