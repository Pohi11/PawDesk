# Proposal

## Why

Every request now reaches `drafting` with a full record of what was checked and, where something stood in the way, a verified proposal. Two things are missing before PawDesk can act:
- a reply to the pet parent;
- a decision about who may let that reply go out.

The reply is human-facing text, which is a job for a model. But a reply is also a promise: a message saying "Biscuit is booked for March 10–13" commits the facility. So the reply must never promise anything the checks didn't confirm, and anything that needed a closer look must wait for a person. That person must be able to approve the reply, fix it, or turn the request down. Their action must resume the run from where it paused.

## What Changes

- **A reply agent** drafts a warm, clear message (subject and body) from structured facts only: the owner's and pet's names on file, the service and dates, and what the checks and resolver found. Customer text is never sent to it.
- **A deterministic promise check** runs on every draft. It flags:
  - dates the checks didn't confirm;
  - commitment words ("booked", "confirmed", "reserved", "approved") in a reply that confirms nothing;
  - any price.
- **Code decides where a draft goes:**
  - it goes to `needs_review` when the request came through `resolving` or the draft fails the promise check;
  - otherwise it goes to `ready`, is approved by the system, and is sent.
  - The reasons for a flag are saved.
- **Staff approval API:**
  - list the requests waiting for review, with their flag reasons;
  - approve, edit and approve, or reject with a reason.
  - Each action is recorded as an Approval with the staff member's name, and it resumes the run.
- **Sending:**
  - the final reply (or a decline for a rejected request) is recorded as the outbound message, once per request;
  - for a confirmed boarding request, the kennel is reserved in the same transaction;
  - a kennel taken in the meantime fails the step instead of double-booking.
- **A decision record** for where the human gate sits.

## Capabilities

### New Capabilities
- `booking-reply`: Drafting the reply from structured facts, the promise check, and the decision between automatic approval and human review.
- `staff-approval`: The review queue and the approve, edit and approve, and reject actions, recorded as approvals and resuming the run.

### Modified Capabilities
- `booking-orchestration`: adds drafting, automatic approval of clean requests, and sending (with the reservation and the outbound message). A finished request is now a `sent` one, and a request waiting for review is left alone.

## Impact

- **Backend:**
  - new `app/reply.py` and `app/prompts/reply.py`;
  - new `app/approvals.py` and API routes in `app/api.py`;
  - `app/orchestrator.py` gains the drafting, ready, approved, and rejected steps;
  - a migration adds `outbound_messages` and the `reply` step result.
- **Tests:**
  - the promise check is tested as a pure function;
  - the reply step against scripted model answers;
  - the API through the FastAPI app against a real database;
  - one real run of a clean request to `sent`, and one of a flagged request through approval to `sent`.
- **Out of scope:**
  - delivering email or text messages (sending is recorded, not delivered);
  - staff sign-in (the API takes a staff name; authentication is a later change);
  - the dashboard's approval screen (Phase 9).
