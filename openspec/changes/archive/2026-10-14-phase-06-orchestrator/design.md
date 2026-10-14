# Design

## Context

- **What the orchestrator connects:**
  - `run_intake()` (message → intent and matched pet) and `run_records()` (image → extracted records) make model calls through the traced client.
  - `compliance.check()`, `load_requirements()`, and `load_evidence()` are deterministic.
  - `capacity.find_kennel()` is deterministic and advisory.
  - `transitions.transition()` is the only way to change a request's state (guard, log row, version check).
- **Tracing:** spans are written in their own transactions (decision record 0006). Model calls have a per-attempt wall-clock deadline.
- **The lifecycle:** `received → extracting → checking → resolving | drafting`, plus `failed` with its retry rule.

See `proposal.md` for motivation and `specs/` for the required behavior.

## Goals / Non-Goals

**Goals:**
- A fixed, readable workflow in plain Python, where the path of every request can be predicted from its data.
- Crash-safe at every step boundary, with no repeated model calls for finished steps.
- Concurrency only where the steps are independent (intake and records).

**Non-Goals:**
- A general workflow engine.
- Multiple concurrent workers (leases or claiming).
- Scheduling or queues.
- The resolver, reply, and approval steps.
- Persisting extracted records as vaccine records.

## Decisions

### D1. A hybrid workflow: code decides the order, models only read
The orchestrator is a plain async function that branches on the request's state. Model calls happen only inside the two reading steps. Every decision after that is code: compliance, capacity, and routing. The comparison with LLM-planned and fully agentic alternatives, and the reasoning, are recorded in [decision record 0008](../../../../docs/decisions/0008-hybrid-workflow-over-agentic.md).

### D2. Durable execution with step checkpoints
- **Saving:** `booking_step_results(booking_request_id, step, output JSONB, created_at)` with a unique `(booking_request_id, step)`. A step's results and the following transition are written in **one transaction** (through `transition()` in the same session).
- **Resuming:** processing reads the request's state and saved results. For each step it either loads the saved result or runs the step. So a crash *between* steps loses nothing, and a crash *inside* a step only repeats that step.
- **Idempotency:** every step is idempotent. Reading steps have no side effects beyond spans (re-running only costs money). The checks are pure reads. The unique constraint makes a duplicate save impossible even if two runs race.

This is the pattern later phases follow (resolver, reply, and approval steps), so it's recorded in [decision record 0009](../../../../docs/decisions/0009-durable-execution-with-step-checkpoints.md).
- *Alternatives:* a workflow engine such as Temporal (the right tool at scale, but a large operational dependency for one workflow); event sourcing (more history than needed; the transition log already records the moves).

### D3. Step layout

| State on entry | Work | Saved results | Moves to |
|---|---|---|---|
| `received` | — | — | `extracting` |
| `extracting` | `asyncio.gather(intake, records)`, with no database session held during the model calls | `intake`, `records` | `checking` |
| `checking` | pet-name cross-check, compliance (records on file plus extracted), capacity (boarding only) | `checks` | — |
| `checking` (after checks) | routing | `route` (target and reasons) | `drafting` or `resolving` |
| `failed` | retry → back to `failed_step`, then continue | — | — |

- The `received → extracting` move is committed **before** the model calls, so a crash during extraction resumes at extraction.
- The checks and routing are cheap and deterministic, so they share one transaction. Crashing between them can't happen without losing both, and re-running them is free.
- Records runs with `booked_pet=None`, because the pet isn't known until intake finishes. The pet-name comparison moves to the checking step, the point where both results come together.

### D4. Concurrency
Intake and records run in `asyncio.gather`. Their inputs (message, pets, time zone, certificate bytes) are read in one session that is closed **before** the model calls start, and their results are saved in a new session afterward. So no `AsyncSession` is ever shared between concurrent tasks (decision record 0003), and no database connection sits idle for the length of a model call. Trace context propagates through `contextvars`, so their spans become siblings under `extract`. If one fails, the other is allowed to finish (`return_exceptions=True`), so its spans close cleanly. The step then fails as a whole.

### D5. Certificate storage
- **Table:** `booking_documents(booking_request_id UNIQUE, mime, sha256, size_bytes, content BYTEA)`.
- **Why the database:** images are at most 5 MB, and keeping them in Postgres makes a resumed run self-contained, with no file-store consistency problem.
- **Type checking:** the same magic-byte sniffing as the records step, applied at attach time.
- *Alternative:* object storage with a path column. Better at scale, but deferred.

### D6. Failures
`LLMError` and `InvalidModelOutput` raised from a step roll back that step's transaction. A fresh session then moves the request to `failed` with `failed_step` and the error. Any other exception is a bug: it propagates and leaves the request in its working state, so it's visible on resume rather than hidden as `failed`.

### D7. Abandoned spans
At the start of processing, any span still `running` in an earlier trace linked to the request is closed as `error` ("abandoned: the process stopped before this work finished"), and those traces get an end time. A single worker processes a request at a time (a non-goal for now), so no live span can be closed by mistake.

### D8. Simulating crashes
Tests inject a `crash_after` hook that raises a `BaseException` subclass right after a chosen checkpoint commits. It bypasses normal error handling, like a killed process would. The command line also supports a real hard stop (`os._exit`) after a chosen step, for the manual kill test.

## Risks / Trade-offs

- [A crash during extraction repeats both model calls, even if one had finished] → It costs money, not correctness. Saving each reading step separately would need a state between intake and records that the lifecycle doesn't have. Accepted for two cheap calls.
- [A single worker is assumed] → The version column and unique checkpoints prevent corruption if two runs race. True parallel workers need leases, which are out of scope.
- [Certificate bytes in Postgres grow the database] → Capped at 5 MB per request. Moving to object storage is a later change.
- [Compliance unions records on file with extracted records] → Extracted records aren't trusted alone: any records issue routes the request to `resolving`, and so to human review later.
