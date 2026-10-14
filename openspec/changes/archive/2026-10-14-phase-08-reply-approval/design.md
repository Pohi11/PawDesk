# Design

## Context

- Requests reach `drafting` with saved `intake`, `records`, `checks`, `route`, and possibly `resolution` results.
- The lifecycle already allows:
  - `drafting → needs_review | ready` (system);
  - `ready → approved` (system);
  - `needs_review → approved | rejected` (staff);
  - `approved | rejected → sent` (system);
  - failure from `drafting`, `approved`, and `rejected`.
- The `approvals` table exists, and a reject requires a reason (database CHECK).
- `structured.extract()` gives validated model output with one repair.

## Goals / Non-Goals

**Goals:**
- A reply that can't over-promise, enforced by code and not by prompt.
- A human gate that is a durable state, so a waiting request survives restarts and resumes on a staff action.
- Sending that is idempotent and can't double-book.

**Non-Goals:** real email delivery, staff authentication, editing anything other than the reply text, re-running checks on a staff edit.

## Decisions

### D1. Where the human gate sits
Recorded in [decision record 0011](../../../../docs/decisions/0011-human-gate-before-sending.md).
- The gate is the `needs_review` state, *after* the reply is drafted and *before* anything is sent or reserved. Staff see the full picture (checks, resolution, draft) and act once.
- Clean requests skip the gate. Every check was deterministic and passed, intake raised no issue (including no instruction-like text), and the draft passed the promise check.

### D2. Reply facts (no customer text)
`reply_facts()` builds the facts:
- `owner_first_name` and `pet_name` from the database rows (on file, not as written in the message);
- `facility`, `service`, `start_date`, `end_date`;
- `situation`;
- `options`: verified options only;
- `vaccines_needed`: from a verified `vaccine_update`.

The situation is decided by code:

| Route | Resolution | Situation |
|---|---|---|
| `drafting` | — | `confirmed` |
| `resolving` | proposed, with at least one verified option | `alternatives` |
| `resolving` | anything else | `under_review` |

`PROMPT_VERSION = "reply-v1"`. Output is `ReplyDraft{subject ≤120, body ≤1500}` through `extract()`, at temperature 0.

### D3. The promise check (`promise_issues(body, facts)`)
Pure and deterministic.
- **Dates:** finds ISO dates (`2027-03-10`), month-name dates (`March 10`, `Mar 10th`, `10 March`, with an optional year), and numeric `3/10`. Each is compared by (month, day) with the allowed dates: the requested start and end, and the start and end of each verified alternative.
- **Commitment words:** `booked`, `confirmed`, `reserved`, `approved` (whole words, any case) are reported when the situation isn't `confirmed`. "Please confirm" is allowed because it asks, it doesn't commit.
- **Money:** `$` or `USD` followed by a number, or a number followed by "dollars".

Findings flag the request. There is no automatic repair, because a person fixing the text is the safer recovery.

### D4. Flag reasons
- `came through resolving: <outcome> (<reason>)`;
- each promise-check finding, prefixed `reply:`.

The saved `reply` result is `{situation, facts, draft, promise_issues, flags, target, prompt_version}`.

### D5. Staff actions (`app/approvals.py`, `app/api.py`)
- `decide(sessions, request_id, action, staff_name, *, reason=None, reply=None)`. In one transaction it:
  - loads the request;
  - refuses unless it's `needs_review` (`NotWaiting` → 409);
  - inserts an `Approval`;
  - transitions with actor `staff` (version check → `TransitionConflict` → 409);
  - commits.
- It then calls `process_request()` to send.
- Routes:
  - `GET /reviews`;
  - `POST /requests/{id}/approve` `{staff_name}`;
  - `POST /requests/{id}/edit-and-approve` `{staff_name, reply}`;
  - `POST /requests/{id}/reject` `{staff_name, reason}`.
- Pydantic bodies validate the input (a blank reason → 422).
- The sessionmaker comes from a FastAPI dependency, so tests can override it.

### D6. Sending (`approved | rejected → sent`)
One transaction:
- **The text:**
  - approved: the edited reply if the latest Approval is `edit_and_approve`, otherwise the draft;
  - rejected: a fixed decline template filled by code. The internal reason is never sent.
- **The reservation:** only when the situation is `confirmed` and the service is boarding. `find_kennel` runs again at send time, then the Reservation is inserted.
  - None free → `StepFailed("no free kennel at send time")`.
  - Another transaction winning the race → `IntegrityError` on the exclusion constraint → the same failure.
- **The record:** an `outbound_messages` row (unique per request: kind `reply` or `decline`, subject, body), then `transition(→ sent)`.

Retrying a failed send is safe: everything above is one transaction, and both the reservation and the message are unique per request.

### D7. Orchestrator steps
- `STEPS` gains `drafting → _draft`, `ready → _auto_approve`, `approved → _send`, `rejected → _send`.
- `needs_review` isn't a step, so processing stops there: that's the pause.
- `failed` with failed step `drafting`, `approved`, or `rejected` is retryable.
- A reply model failure (`LLMError` or `InvalidModelOutput`) fails `drafting`.

## Risks / Trade-offs

- [The date pattern misses unusual formats ("the 10th")] → It can only fail to flag, and a missed date is still under the commitment-word and review rules. The patterns are tested, and the list is easy to extend.
- [No authentication: anyone who can reach the API can approve] → Acceptable for a local demo, and noted for the deployment phase.
- [Clean requests are sent with no human] → That's the point of the deterministic checks. Every one of them is traced and auditable.
