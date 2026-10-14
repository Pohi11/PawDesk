# Design

## Context

- The `traces` and `spans` tables exist, with kinds, statuses, an exact `NUMERIC` cost, and JSONB input/output.
- Database access is async SQLAlchemy with asyncpg (decision record 0003).
- Tests run against a real Postgres test database inside rolled-back transactions.
- The Phase 0 smoke script calls OpenRouter with the `openai` SDK, untraced.
- OpenRouter returns usage and `usage.cost` on every response, may send `Retry-After` on 429 and 503, and can return HTTP 200 with an `error` body and no `choices`.

See `proposal.md` for motivation and `specs/` for the required behavior.

## Goals / Non-Goals

**Goals:**
- A model call is impossible without a trace, and every attempt is visible in its span.
- Tracing works the same way for sequential, nested, and concurrent (`asyncio.gather`) work, without passing ids through every function.
- No test ever contacts the real provider unless it is explicitly opted in.

**Non-Goals:**
- Streaming.
- Parsing and validating structured output (Phase 4 builds on `response_format` pass-through).
- Exporting to an external tracing backend.
- Sampling.

## Decisions

### D1. Own the retry loop; the SDK's retries are disabled
The `openai` client is created with `max_retries=0`. `app/llm.py` runs the loop itself, so each attempt's outcome, wait, and status land in the span, and the rules for which failures to retry live in one readable table (D5).
- *Alternatives:* the SDK's built-in retries are invisible to tracing and use their own classification. A retry library (for example tenacity) would add a dependency for about 30 lines of logic that should be read and tested directly.

### D2. One `llm` span per call; attempts go in attributes
A call made of several attempts is one span. `attributes.attempts` lists each attempt: `n`, `outcome` (`ok`, `retryable`, `fatal`), `http_status`, `error`, `waited_s`, and `latency_ms`. Token counts and cost come from the successful attempt. Failed attempts report no usage.
- *Alternative:* one span per attempt. That's noisier on the timeline, and per-attempt cost is almost always zero.

### D3. Context propagation with `contextvars`
`app/tracing.py` holds the current trace id and current span id in `ContextVar`s.
- `start_trace(name, booking_request_id=None)` and `span(name, kind, input=None)` are async context managers. They set the variables on entry and restore them on exit.
- `asyncio.gather` runs each coroutine as a task with a **copy** of the current context. So concurrent children inherit the same parent, and anything one child sets is invisible to its siblings. That's exactly the "concurrent siblings" requirement, with no extra code.
- *Alternatives:* passing trace and parent ids explicitly through every function (verbose, and easy to forget, which would create orphaned spans); the OpenTelemetry SDK (a full export pipeline when Postgres is the only backend; an OTLP exporter can be added later because the data model already matches).

### D4. Span writes are independent, short transactions
A `Tracer` owns its own `async_sessionmaker`. Each span is written twice: an INSERT with status `running` at start, and an UPDATE with the end time, status, output, usage, and attributes at the end. Each write is its own transaction, committed immediately. Business code never shares a session with the tracer.

This affects every later phase, because the orchestrator and agents rely on it, so it's recorded as [decision record 0006](../../../docs/decisions/0006-tracing-and-model-calls.md).
- *Why:* a span describing failed work has to survive that work's rollback. That's the point of tracing. A `running` row also lets the dashboard (Phase 9) show work in progress.
- *Cost:* two extra round trips per span, which is negligible next to multi-second model calls.

### D5. Failure classification table
| Condition | Outcome |
|---|---|
| Timeout or connection error | retryable |
| HTTP 408, 429, 500, 502, 503, 504 | retryable |
| HTTP 400, 401, 402, 403 (and any other 4xx) | fatal |
| HTTP 200 with `error` and no `choices` | retryable if `error.code` is in the retryable set, otherwise fatal |

Fatal errors and exhausted retries raise `LLMError`, which carries the final classification. The span records the error.

### D6. Backoff: `Retry-After` first, otherwise full jitter
- **Wait before attempt n+1:**
  - the `Retry-After` value in seconds, capped at 60 seconds, when present;
  - otherwise `uniform(0, min(cap, base × 2^(n−1)))`, with base 1 second and cap 20 seconds. That's "full jitter": spreading retries randomly avoids many clients retrying in lockstep.
- **Testing:** `sleep` and the random source are injectable, so retry tests run instantly and deterministically.

### D7. Timeouts
Each attempt gets `timeout=settings.llm_timeout_seconds` (default 30) through the SDK request options. A timeout is retryable (D5). The total time is therefore bounded by attempts × (timeout + wait).

### D8. Recording without secrets
- The span input is `{"messages": scrub(messages), "model": ..., "params": {...}}`. Headers and the API key are never part of span data: the key is only given to the SDK client.
- `scrub()` deep-copies the messages and replaces every `image_url` whose URL starts with `data:` by `"[image sha256=<hex> bytes=<n>]"`. The hash still lets a later record be matched to the exact image that was processed.
- A test scans every stored trace and span for the key string.

### D9. Exact cost
`usage.cost` arrives as a JSON number. It is converted with `Decimal(str(value))`, which keeps the printed digits (for example `9.42e-05` becomes exactly `0.0000942`). A missing cost stays `None` (spec: never estimated).

### D10. Public interface
`await complete(messages, *, name, model=None, response_format=None, temperature=None) -> LLMResult` (text, model, generation id, finish reason, tokens, cost, span id). `response_format` is passed through to the provider unchanged and recorded in the span's params, ready for the intake agent's structured output. The client is built by a factory that accepts an optional `httpx` transport. Tests pass `httpx.MockTransport`.

### D11. Live test is opt-in
A `live` pytest marker is registered and excluded by default (`-m "not live"`). Running `uv run pytest -m live` makes one real call and checks the span it stored. The smoke script `scripts/hello_openrouter.py` becomes a traced call that prints the span id.

## Risks / Trade-offs

- [A trace linked to a booking request that was never committed would violate the foreign key] → Callers link a trace only to a request that already exists. Traces for not-yet-stored work leave `booking_request_id` empty.
- [Tracer writes in tests are committed, not rolled back] → The tracing test fixture records the ids it created and deletes them on teardown.
- [`Retry-After` could ask for a very long wait] → It's capped at 60 seconds. Beyond that, the call fails and the orchestrator's retry and `failed` state take over.
- [Recording full prompts stores pet-parent messages] → All data in this project is synthetic. A production deployment would add field-level redaction of personal data, noted as an open question for later.

## Open Questions

- Per-facility personal-data redaction rules for prompts, for real deployments. This doesn't affect this change's behavior.
