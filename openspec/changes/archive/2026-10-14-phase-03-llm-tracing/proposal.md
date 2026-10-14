# Proposal

## Why

Every later phase calls a language model: intake, records extraction, the resolver, and the reply. Each of those calls costs money, can fail in several ways, and processes untrusted input. Without one traced client, failures would be handled inconsistently, retries could hammer the provider or double the cost unseen, secrets or raw images could end up in logs, and the dashboard would have nothing to show. Tracing has to exist before the first agent does, so that no model call is ever untraced.

## What Changes

- Add a single async model client that is the only way to call a model. It:
  - refuses to run outside an active trace,
  - applies a timeout to each attempt,
  - retries only transient failures, with exponential backoff and jitter, honoring `Retry-After`,
  - never retries permanent failures,
  - treats an HTTP 200 that carries an error body as a failure,
  - records exactly one `llm` span per call.
- Record the cost reported by the provider as an exact decimal. If the provider doesn't report one, the cost stays empty and is never estimated.
- Never record secrets. The API key and request headers are never stored, and inline image data in prompts is replaced by a hash and a size.
- Add tracing helpers: start a trace, and open nested spans for code and tool work. Parent links follow the code structure, including concurrent work.
- Write spans in their own transaction and commit them immediately, so a span survives even when the work it describes is rolled back. A span is stored as `running` when it starts and finished when it ends.
- Add an `attributes` field to spans for structured metadata (attempts, finish reason, provider, generation id, request parameters), modeled on OpenTelemetry span attributes.
- Turn the Phase 0 smoke script into a traced call that writes a real span to the development database.

## Capabilities

### New Capabilities
- `llm-client`: How the system calls a language model: the trace requirement, timeouts, retry and failure classification, cost recording, and keeping secrets out of the record.

### Modified Capabilities
- `run-tracing`: adds requirements for recording spans while work runs (running, then finished), parent links that follow nested and concurrent code, spans that survive rolled-back work, and span attributes. The existing storage requirements are unchanged.

## Impact

- **Backend:** new modules `app/tracing.py` and `app/llm.py`, a migration adding `spans.attributes`, and an updated `scripts/hello_openrouter.py`. No new dependencies: the `openai` SDK and `httpx` are already installed.
- **Configuration:** new optional settings for the attempt timeout and the maximum number of attempts.
- **Tests:** model calls are tested against a fake HTTP transport, so CI never calls the real model. One opt-in `live` test calls OpenRouter.
- **Out of scope:** streaming responses, structured-output parsing and validation (the intake agent's job), prompt caching, and the dashboard views of spans.
