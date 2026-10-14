# 0011 — The human gate sits after the draft and before anything is sent or reserved

- **Date:** 2026-10-14
- **Status:** Accepted

## Context

A reply to a pet parent is a promise, and sending it (with a kennel reservation for a confirmed stay) is the first thing PawDesk does that can't be quietly undone. Some requests can be decided with full confidence by code: every check is deterministic, and all of them passed. Others needed resolving, carry an issue (an unknown pet, unreadable records, instruction-like text), or produced a draft that says more than the checks confirmed. A person must look at those before anything goes out. Where to put that checkpoint, and how a paused run continues, shapes the whole approval flow.

## Options considered

1. **A human approves everything.** It's the simplest rule and has no automation risk, but staff time goes into rubber-stamping requests the checks already decided.
2. **A gate before the reply is drafted.** Staff decide first, then a model writes the reply. But staff decide without seeing what will be said, and the model's text goes out unreviewed.
3. **A gate after drafting, before sending.** Flagged requests stop in `needs_review` with the checks, the resolution, the draft, and the reasons for the flag. Staff approve, edit, or reject once. Clean requests skip the gate.
4. **A gate after sending** (review samples afterward). Fast, but a wrong promise has already reached the customer.

## Decision

Option 3.

- **The gate is a state, not a running process.** `needs_review` is persisted like every other state, so a paused request survives restarts and holds no resources.
  - A staff action records an Approval and moves the request in one transaction, guarded by the version check.
  - Processing then resumes from the new state, exactly as after a crash (decision record 0009).
- **Who waits is decided by code:**
  - every request that came through `resolving`;
  - every draft that fails the deterministic promise check (unconfirmed dates, commitment words when nothing was confirmed, prices).
- **Clean requests** (every check passed, intake raised nothing, and the draft promises nothing extra) are approved by the system and sent.
- **Staff can:**
  - approve the draft;
  - replace its text;
  - reject with a reason, which is recorded and never sent to the customer. The customer gets a fixed decline.
- **The reservation for a confirmed stay is made when sending,** in the same transaction as the message. A kennel taken since checking fails the step instead of double-booking.

## Consequences

- **Good:** Staff time goes only to requests with a reason to look, and each one arrives with that reason written down.
- **Good:** Nothing irreversible happens before the gate, and nothing after it happens twice: one message and one reservation per request, both enforced by the database.
- **Cost:** Clean requests are sent with no human involved. That is safe only because every check before it is deterministic and tested. A new check that relies on a model must flag, not pass.
- **Cost:** Staff edits are sent as written and aren't re-checked. Staff are trusted, and their edit is recorded on the Approval.
- **Cost:** Staff sign-in doesn't exist yet. The API records a name and must not be exposed before authentication is added.
