# 0009 — Durable execution through step checkpoints in Postgres

- **Date:** 2026-10-14
- **Status:** Accepted

## Context

Processing a booking request takes several seconds of model calls followed by database checks. A process can die at any point: a deploy, an out-of-memory kill, a hung provider connection. Two things must hold after a crash:

- No work is lost. The request can continue instead of being stuck or starting over.
- Nothing happens twice when a step is retried. That means no second reservation, no second email, and ideally no paid model call repeated for a step that already finished.

Doing a step twice must have the same effect as doing it once (idempotency), and the system must know which steps already finished (durability).

## Options considered

1. **Re-run everything from the start.** Simple, but it repeats every model call after a crash and depends on every step being free of side effects forever.
2. **A workflow engine** (Temporal, or a queue with step state). Durable execution, timers, and retries built in. But it's a separate service to run and learn, for one short linear workflow.
3. **Event sourcing.** Store every event and rebuild state from them. More history than needed: the transition log already records every state change.
4. **Step checkpoints in the existing database.** Save each step's result in a `booking_step_results` table, in the same transaction as the state change that follows it. A run reads the request's state and saved results, and runs only the steps without a result.

## Decision

Option 4.

- `booking_step_results` has one row per (request, step), enforced by a unique constraint.
- A step's results, the request's state change, and its transition log row are committed in one transaction. Either all exist or none do.
- The `received → extracting` move is committed before any model call, so a crash during extraction resumes at extraction.
- Each step is idempotent:
  - The reading steps have no side effects beyond spans.
  - The checks are pure reads.
  - Later steps with side effects rely on database uniqueness (one reservation per request) rather than on being run only once.
- A step that fails in an expected way (model unavailable, output invalid after repair) moves the request to `failed` with the error. The next run retries from that step. Any other exception is treated as a bug and left visible in the working state.
- When a request is processed again, spans that a killed run left `running` are closed as abandoned.

## Consequences

- **Good:** A crash between steps loses nothing, and finished model calls are never repeated.
- **Good:** No new infrastructure. The checkpoint, state, and log share one transaction in the same database.
- **Cost:** A crash *inside* a step repeats that whole step, including both concurrent model calls in extraction. That costs money, not correctness.
- **Cost:** It assumes one worker processes a request at a time. The version column and unique checkpoints prevent corruption if two runs race, but running many workers safely needs leases, a later change.
- **Cost:** No built-in timers or scheduled retries. Retrying a failed request is an explicit call.
