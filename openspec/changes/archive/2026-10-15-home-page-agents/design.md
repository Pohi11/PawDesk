# Design

## Context

- **Four parts of the workflow use a model** (decision record [0008](../../../../docs/decisions/0008-hybrid-workflow-over-agentic.md)):
  - intake (`app/intake.py`) and records (`app/records.py`) each make one model call and return a validated schema;
  - the resolver (`app/resolver.py`, record [0010](../../../../docs/decisions/0010-bounded-proposal-only-resolver.md)) runs a loop of up to 6 model calls and 12 calls to 3 read-only tools, then proposes one offer;
  - the reply (`app/reply.py`) makes one model call from facts code built.
- **Code checks each output** before it counts: confidence below 0.7, ambiguities, date and label checks, the promise check on the draft.

## Goals / Non-Goals

**Goals:** a visitor can name each agent, say what it sees and returns, and say what stops it from deciding anything.

**Non-Goals:** diagrams of the agents' internals; changes to the agents.

## Decisions

### D1. A table, one row per agent
- **The content is a grid by nature:** four agents by three questions (reads, returns, what code checks). A table shows that, where four cards would hide it.
- **Below 1024 px** each row stacks, and each cell carries its column's name: four columns of prose are too narrow to read at tablet width.
- **Each agent's name says how much of it is a model:** "one model call" or "a loop of up to 6 model calls". Calling all four "agents" is the project's own vocabulary; the table states which one loops.

### D2. The steps section shrinks
- **The agents section holds what each agent sees and returns,** so each step keeps only the order and who runs it. The step text names the agent so the two sections connect.

### D3. Facts come from the code
- **Each cell restates a check the code makes,** with its threshold where it has one (0.7 confidence, 6 model calls, 12 tool calls), so the copy guide's rule on true claims holds.

## Risks / Trade-offs

- [Thresholds in the copy can drift from the code] → They are the constants `CONFIDENCE_THRESHOLD`, `MAX_TURNS`, and `MAX_TOOL_CALLS`; a change to them is a spec change and gets a home page edit with it.
