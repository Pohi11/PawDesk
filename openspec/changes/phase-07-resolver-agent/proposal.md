# Proposal

## Why

After checking, a request lands in `resolving` when something stands in the way: no kennel is free for those nights, or a required vaccine won't cover the stay. Today it simply stops there. A good front desk doesn't just say no. It looks for what would work: the same stay a few days later, a larger kennel, or an updated vaccine record. Finding and combining those options is open-ended enough to be a fit for a small agent: a model that calls tools in a loop. But an agent is the least predictable pattern there is (decision record 0008), so this one is fenced in:
- it reads no untrusted text;
- its tools only read;
- its only output is a proposal that code re-checks;
- it stops when it's done, stuck, or out of steps.

## What Changes

- **Tool calling in the model client:** tools can be offered on a model call, and the model's requested calls come back as structured data. They are recorded on the span.
- **A resolver agent** with a hand-written loop:
  - call the model, run the tools it asks for, append the results, repeat;
  - stop at a step limit;
  - stop on a **stuck guard**: the same tool called again with the same arguments.
- **Four read-only tools**, bound to the request so the model can only choose dates or sizes:
  - `find_alternative_dates`: nearby stays of the same length;
  - `list_missing_vaccines`: what doesn't cover a given window;
  - `check_kennel_sizes`: free kennels per size class;
  - `propose_offer`: the only way to finish.
- **Proposals are verified by code:** each proposed option is re-checked against capacity and compliance and marked verified or not, with the problems that would remain.
- **Code decides whether the agent runs at all:** only problems an alternative can fix (capacity, vaccine coverage) go to the agent. Anything else (an unknown pet, unreadable input, suspected injection) goes straight to a person, with no model call.
- **The orchestrator continues past `resolving`:** the resolution is saved with the move to `drafting`, durably like the other steps. Failures move the request to `failed` and are retried as before.
- **A decision record** for why the agent is bounded and proposal-only, and why its loop is hand-written.

## Capabilities

### New Capabilities
- `booking-resolution`: Deciding whether a request's problems can be resolved by alternatives, running the bounded resolver agent with its tools and stop conditions, and verifying its proposal in code.

### Modified Capabilities
- `llm-client`: adds a requirement for offering tools on a model call and returning the requested tool calls.
- `booking-orchestration`: adds the resolving step (the resolution is saved with the move to `drafting`), and changes what a finished request is (`drafting` and later, no longer `resolving`).

## Impact

- **Backend:**
  - `app/llm.py` gains tool calling;
  - new `app/resolver.py` (eligibility, tools, loop, verification) and `app/prompts/resolver.py`;
  - `app/orchestrator.py` gains the resolving step;
  - a migration allows the new `resolution` step result.
- **Tests:**
  - the loop is tested against scripted model turns: proposal, stuck guard, step limit, unknown tool, invalid arguments, and an attempt to call a tool that would approve;
  - every tool is tested against the database;
  - one opt-in live test checks that the configured model really calls tools;
  - real runs from the command line: a request whose nights are full, and one with an expired vaccine.
- **Out of scope:**
  - writing the reply to the customer and the human approval (Phase 8);
  - reserving a kennel;
  - voting or evaluating the resolver at scale.
