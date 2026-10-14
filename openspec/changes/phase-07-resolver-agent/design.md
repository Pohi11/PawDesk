# Design

## Context

- **What exists:**
  - The orchestrator stops a request in `resolving`, with saved `checks` and `route` results that list every problem in structured form.
  - The lifecycle allows `resolving → drafting` (system) and `resolving → failed`. Nothing else leaves `resolving`, so the guard already makes self-approval impossible.
  - The deterministic building blocks the tools need: `capacity.find_kennel()`, `compliance.check()`, and the loaders for requirements and records on file.
- **What doesn't:** the model client returns text only. There is no tool calling yet.

See `proposal.md` for motivation and `specs/` for the required behavior.

## Goals / Non-Goals

**Goals:**
- A real agent loop that's small enough to explain line by line, with every turn and tool call traced.
- An agent that can't be steered by customer text and can't approve anything, by construction and not by prompt.
- Proposals that staff can trust because code re-checked them.

**Non-Goals:**
- Agent frameworks (compared in a later phase).
- Reserving kennels or contacting the customer.
- Evaluating the resolver across many cases.
- Voting.

## Decisions

### D1. A bounded, proposal-only agent with a hand-written loop
The reasoning (why an agent here at all, why no framework, why proposals only) is recorded in [decision record 0010](../../../docs/decisions/0010-bounded-proposal-only-resolver.md). In short:
- a deterministic search *could* list candidate windows;
- the agent earns its place by combining fixes when several problems interact (dates that fix capacity but break a vaccine, a larger kennel, an updated record) and by writing a short summary for staff;
- every fence below keeps it from becoming the least predictable part of the system.

### D2. Code decides eligibility (no model call for the wrong problems)
`resolution_scope(intake, records, checks)` is pure. The agent runs only when:
- intake and records are clear (or records were skipped);
- the pet is matched and the certificate names no other pet;
- compliance and capacity were checked;
- every remaining problem is either capacity `none_free` or a vaccine status in {missing, expired, expires_during_stay, not_yet_given}.

`unknown_expiry` needs a person to read a record, so it goes to a person too. Everything else is `not_attempted`, with the problems listed.

### D3. The prompt is built from code values only
- **System prompt:** the role, the rules (only propose; use tool results; never invent dates), and `PROMPT_VERSION = "resolver-v1"`.
- **User turn:** a JSON object of service, species, size class, requested start and end, today, and the problems, as `{"vaccines": [{vaccine, status}], "capacity": "none_free" | null}`.
- **Excluded:** the pet's name, the customer's message, special notes, and certificate text. That removes the injection surface instead of defending it.

### D4. Tools
Each tool takes a Pydantic argument model (`extra="forbid"`), whose JSON schema is offered to the model. The request context is bound in code: pet, facility, service, requested dates, today, and evidence (records on file ∪ extracted). Every tool result is a JSON object, and errors come back as `{"error": "..."}`.

| Tool | Arguments | Result |
|---|---|---|
| `find_alternative_dates` | `max_shift_days` (1–14, default 7) | Up to 5 windows with the same number of days. The start is shifted by ±1…N days, never before today, ordered by distance (earlier first on ties). Each window has: kennel (boarding: a free kennel name or none), compliance outcome and failing vaccines. Only windows where a kennel is free (or none is needed) are returned. |
| `list_missing_vaccines` | `start_date`, `end_date` | For that window: each required vaccine that isn't `ok`, with its status and the latest known expiry. |
| `check_kennel_sizes` | `start_date`, `end_date` (end after start) | Free kennel count per size class the facility has, plus the pet's own class. |
| `propose_offer` | `options` (1–3), `summary` (≤ 400 chars, for staff) | Ends the loop. Options form a discriminated union: `{kind: "alternative_dates", start_date, end_date}`, `{kind: "larger_kennel", size_class}`, `{kind: "vaccine_update", vaccines: [...]}`. |

- The windows' dates are validated against a 365-day horizon, the same as intake's.
- A `larger_kennel` must be a strictly larger dog size class (small < medium < large < xlarge). A smaller or equal size, or any size for a cat, is answered with an error result.

### D5. The loop
```
messages = [system, user(context)]
for turn in 1..MAX_TURNS (6):
    result = complete(messages, tools=TOOL_SCHEMAS, temperature=0, name="resolver.turn")
    if no tool calls:              -> escalated("no proposal")
    messages += result.assistant_message
    for call in result.tool_calls:
        key = (name, canonical JSON of the parsed arguments, or the raw text if unparsable)
        if key seen before:        -> escalated("stuck: repeated <name> with the same arguments")
        if total tool calls > 12:  -> escalated("step limit: 12 tool calls")
        run the tool (or answer the error) in a "tool" span; append a tool message
        if propose_offer was valid: -> verify, then proposed
-> escalated("step limit: 6 model calls")
```
- **Any earlier call, not just the previous one:** within a run, tools are deterministic, so any repeat returns nothing new. Checking all earlier calls also catches A, B, A, B cycles.
- **A valid `propose_offer` ends the run immediately:** later calls in the same turn are not run.
- **Exceptions:** a tool's validation error is data for the model. Any other exception inside a tool is a bug and propagates.

### D6. Verification
For each option, code re-runs the checks it implies:
- **Dates:** a kennel for the new window (boarding) and compliance for the new window.
- **Larger kennel:** `find_kennel` with that size class for the requested dates, plus compliance for the requested dates.
- **Vaccine update:** the named vaccines must equal the vaccines failing for the requested dates, and capacity for the requested dates is reported.

Each option is stored as `{..., verified: bool, remaining_problems: [...]}`, where verified means nothing remains. Phase 8 offers only verified options to the customer, and a person always reviews requests that came through `resolving`.

### D7. Orchestration and durability
- `STEPS[State.RESOLVING] = _resolve`.
- The step loads the saved results, runs eligibility and then (maybe) the loop inside a `resolve` span, and saves `resolution` with `resolving → drafting` in one transaction (decision record 0009).
- No session is held while the model works, as in extraction. The loop receives a session factory, and each tool call and the final verification open a short session of their own. A single session held across up to six model calls would leave a connection idle in an open transaction for the whole run.
- The new step name `resolution` needs a migration for the step CHECK constraint.
- **Failures:** `LLMError` → `failed` (failed step `resolving`), and the next run retries. A crash mid-loop repeats the loop (cost, not correctness, the same trade-off as extraction).
- **Finished** now means `drafting` and beyond.

### D8. Tool calling in the client
- `complete(..., tools=None)` passes `tools`, and sets `require_parameters` when tools or a response format are present.
- `LLMResult` gains:
  - `tool_calls: tuple[ToolCall(id, name, arguments), ...]`;
  - `assistant_message`, which is the dict to append, including `tool_calls`, so the conversation is valid on the next turn.
- The span output adds `tool_calls` (name and arguments).
- Tool results are appended as `{"role": "tool", "tool_call_id": id, "content": json}`.

## Risks / Trade-offs

- [The configured model may call tools poorly] → The opt-in live test checks basic tool use. A real run records the turns and cost. Escalation is always a safe ending.
- [A deterministic search could replace the agent] → Acknowledged in decision record 0010. The agent is kept for combining fixes and summarizing, and its cost is bounded (≤ 6 calls).
- [The 365-day horizon and ±14-day search range are policy guesses] → They are constants in one place, and easy to change.
- [Rerunning a crashed loop can produce a different proposal] → Only the saved result counts, and it's saved once.
