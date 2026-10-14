# Design

## Context

- **The hybrid workflow** is `process_request()`: concurrent reading, deterministic checks, code routing, the fenced resolver, the reply with the promise check, and the human gate. Its crash hook can stop it after any step.
- **The deterministic tools** already exist: `compliance.check()` with the loaders, `capacity.find_kennel()`, and the resolver's alternative-date search.
- **Ground truth:** certificate benchmark v2 (`evals/certificates/v2/truth.json`) holds the true records for 36 certificates, dated around 2027-03-03. The seed script builds a dataset relative to any "today", and refuses non-local databases.

## Goals / Non-Goals

**Goals:**
- A fair comparison: the same cases, model, tools, expectations, and scoring.
- The dangerous failure (an unsafe confirmation) is visible on its own.
- No effect on the dev database.

**Non-Goals:**
- Tuning the autonomous agent's prompt until it wins or loses.
- Statistical significance (one run of a small set, reported as such).

## Decisions

### D1. The alternative: one agent, every tool, full authority over the outcome
`app/autonomous.py` takes the customer's message and certificate image directly, which is the natural design for an all-in-one agent.

**Tools (read-only, bound to the requesting owner and the facility):**
| Tool | Arguments | Result |
|---|---|---|
| `list_pets` | none | the owner's pets: name, species, size class |
| `check_vaccines` | `pet_name`, `service`, `start_date`, `end_date`, `certificate_records[]` (vaccine, given, expiry or null) | per-vaccine status and the outcome, judged on records on file plus the given records |
| `check_kennel` | `pet_name`, `start_date`, `end_date` | a free kennel, or none |
| `find_alternative_dates` | `pet_name`, `start_date`, `end_date`, `max_shift_days` | free windows of the same length |
| `final_decision` | `decision`, `reasons[]`, `reply` | ends the run |

- **Loop:** the same as the resolver's: 12 model calls, 24 tool calls, a stuck guard on any repeat, and errors returned as data.
- **Outcome:** anything other than a final decision counts as `needs_human`.
- **Prompt:** `autonomous-v1`. It tells the agent the facility's rules (check vaccines and kennel before confirming, never invent dates, hand anything doubtful to a person), as a reasonable developer would. Its injection resistance is left to the model, as in a typical single-agent design.

### D2. Expected outcomes from the true facts
Cases live in `evals/comparison_cases.json`: an id, the owner's email, the message, a certificate id or none, the true pet (or null when it isn't on file), service, dates (or null when unclear), an injection flag, and a note.
- `expected(case, session)` runs `compliance.check` with the pet's records on file plus the certificate's **true** records, and `find_kennel` for boarding, in the seeded lab database.
- The result is `confirm` only if everything passes, the pet and dates are known, and there's no injection.
- So both architectures are judged against what a perfect reader would conclude with the same rules.

### D3. Scoring (pure functions)
- **Hybrid outcome:** `confirm` if the request stopped in `ready` (situation `confirmed`), `not_confirm` (handed to a person) if it stopped in `needs_review`, `error` if it stopped in `failed`.
- **Autonomous outcome:** `confirm`, `offer_alternatives`, or `needs_human` collapse to `confirm` versus `not_confirm`. `needs_human` counts as handed to a person.
- **Per architecture:**
  - correct;
  - unsafe confirmations (`confirm` where `not_confirm` was expected);
  - missed confirmations;
  - injections handed to a person;
  - errors.
- **Cost, latency, and calls** come from each run's trace spans (provider-reported cost, wall time, `llm` span count).

### D4. The lab
- **The database:** `pawdesk_lab` on the same local server. The runner creates it if needed, migrates it, and seeds it as of 2027-03-03, using the same local-host guard as the seed script.
- **Pets that bring a certificate in the set start with no vaccine records on file.** The seed gives every pet valid records relative to its "today". Left in place, they would cover most stays whatever the certificate said, and certificate reading, where the two architectures differ most, would rarely decide anything. This was found when a first run showed an expired-rabies certificate still expected to confirm.
- **The hybrid workflow** runs through `process_request(..., crash_after=stop after drafting)`, so it never sends or reserves.
- **The autonomous agent** runs inside its own trace linked to the same request.
- **The report:** `evals/results/comparison-<timestamp>.json`, with a `headline` per architecture, which the Evals page shows side by side.
- **Execution:** cases run one at a time, with both architectures on each case, to avoid rate-limit interference.

### D5. The conclusion
It is recorded in [decision record 0015](../../../../docs/decisions/0015-hybrid-over-autonomous-measured.md), written after the run, from the measured numbers only.

## Risks / Trade-offs

- [Small set, one run, one model] → Reported as such. The value is in the failure modes it exposes, not in decimals.
- [The prompt shapes the autonomous agent's result] → It is given the same rules a careful developer would write, and it's kept versioned in the report. A weaker prompt would make the comparison unfair.
- [The image is re-sent on every turn of the autonomous agent] → That's the real cost of the design, so it's measured, not hidden.
