# Proposal

## Why

A booking starts as a free-text message from a pet parent, for example "can biscuit stay fri-mon? he gets anxious at night". Every later step (compliance, capacity, resolution, the reply) needs that turned into exact, typed values: which pet, which service, which dates. Reading messy language is the one job a language model is genuinely good at. It's also where untrusted input enters the system. So the output has to be strictly validated, and the input must be unable to change anything beyond the description of the request.

## What Changes

- Add an intake step that turns a pet-parent message into a validated `BookingIntent`: pet name, service, start and end dates, special notes, the model's confidence, and anything it found ambiguous.
- Request structured output from the provider using a strict JSON schema generated from the same Pydantic model used for validation, and route such requests only to endpoints that support them.
- Always validate the model's output with Pydantic, whatever the provider promised. On a validation failure, make exactly one repair attempt that shows the model its validation errors.
- Run deterministic checks in code after parsing:
  - dates are in order, not in the past, and within a booking horizon;
  - day services fit a single day;
  - the pet name matches one of the owner's pets;
  - low confidence or reported ambiguities send the request to human review.
- Isolate the untrusted message:
  - it is wrapped as data, never as instructions;
  - oversized messages are refused before any model call;
  - the output schema has no field that could approve, price, or prioritize anything, and unknown fields are rejected.
- Add a labeled set of 16 messy messages (including 3 prompt-injection attempts) and an evaluation command that runs it against the real model and reports results.

## Capabilities

### New Capabilities
- `booking-intake`: Turning an untrusted pet-parent message into a validated booking intent plus a list of issues, including repair of invalid output, deterministic semantic checks, pet matching, and resistance to prompt injection.

### Modified Capabilities
- `llm-client`: adds a requirement that structured-output requests are routed only to provider endpoints that support the requested parameters. The existing requirements are unchanged.

## Impact

- **Backend:**
  - new `app/intake.py` (schema, prompt, pipeline) and `app/prompts/intake.py` (versioned prompt text);
  - a small change in `app/llm.py` to add provider routing preferences when a `response_format` is given;
  - a labeled case file under `backend/evals/`;
  - an evaluation script `scripts/eval_intake.py`.
- **Tests:** pipeline behavior (validation, repair, semantic checks, injection handling) is tested against scripted model responses, with no real calls. The labeled set runs against the real model only through the opt-in eval command, and its measured result is recorded.
- **Out of scope:**
  - wiring intake into the booking orchestrator and state transitions (Phase 6);
  - reading vaccine certificates (Phase 5);
  - multi-pet or multi-service requests in one message (flagged as ambiguous rather than split);
  - sending any reply.
