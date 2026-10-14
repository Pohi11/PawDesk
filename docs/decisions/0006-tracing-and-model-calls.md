# 0006 — Spans are written independently; every model call goes through one traced client

- **Date:** 2026-10-14
- **Status:** Accepted

## Context

Every later phase adds steps that call a language model or run tools: intake, records extraction, the resolver, and the reply. Operators need to see each step: what went in, what came out, how long it took, what it cost, and why it failed. The most important case is the **failed** one, and failed work usually ends with its database transaction rolled back. If spans were written in that same transaction, the record of the failure would vanish with it.

Model calls are also where cost, latency, retries, and leaked secrets come from. If each agent called the provider in its own way, those concerns would be handled inconsistently, or not at all.

## Options considered

1. **Spans written in the business transaction.** Simple and consistent, but failures erase their own record, and nothing is visible until the step commits.
2. **Spans buffered in memory and flushed at the end of a run.** Fewer writes, but a crash loses the whole trace, and nothing can show live progress.
3. **Spans written in their own short transactions** (insert as `running` at start, update at end), plus a single traced model client that all model calls must use.
4. **The OpenTelemetry SDK with an external collector.** Industry standard, but it adds infrastructure, and the dashboard would have to query a second store.

## Decision

Option 3.

- `app/tracing.py` owns a session factory that business code never uses. Each span write is its own transaction, committed immediately.
- Trace context lives in `contextvars`, so nested and concurrent work gets correct parent links without passing ids around.
- `app/llm.py`'s `complete()` is the only code that calls a model.
  - It refuses to run outside a trace.
  - It owns the retry loop, so every attempt is recorded.
  - It records cost exactly as the provider reports it, never estimated.
  - It never stores keys, headers, or raw image data.
- The data model (trace, span, parent, kind, status, attributes) mirrors OpenTelemetry, so an exporter can be added later without changing callers.

## Consequences

- **Good:** A failed or crashed step still leaves a span with its error. `running` rows let the dashboard show live progress.
- **Good:** One place enforces "no untraced model calls", along with retries, timeouts, and secret hygiene.
- **Cost:** Two extra database round trips per span, which is negligible next to model latency.
- **Cost:** Traces can reference a booking request only after that request is committed (foreign key). Work on not-yet-stored requests is traced without the link.
- **Cost:** Test fixtures must clean up committed tracing rows, because they aren't covered by the per-test rollback.
