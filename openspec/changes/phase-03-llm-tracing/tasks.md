# Tasks

## 1. Span attributes

- [x] 1.1 Add `spans.attributes` (JSONB, not null, default `{}`) to the model and a migration. Verify with `alembic check` and the attributes default and round-trip tests in `tests/test_run_tracing.py`.

## 2. Tracing

- [x] 2.1 Implement `app/tracing.py`: `Tracer` with its own sessionmaker, `start_trace()`, `span()`, and the context variables. Verify with `tests/test_tracing.py`, covering a running span visible from another connection, failing work recorded and re-raised, nested parent, concurrent siblings, and a span surviving a rolled-back business transaction.
- [x] 2.2 Write [decision record 0006](../../../docs/decisions/0006-tracing-and-model-calls.md) (independent span writes; every model call goes through the traced client). Verify the file exists and that design D4 links to it.

## 3. Model client

- [x] 3.1 Add `scrub()` and the failure classification (design D5, D8) with unit tests in `tests/test_llm.py`, covering a data-URL image replaced by its hash and size, and every status in the classification table. Verify that the tests pass.
- [x] 3.2 Implement `complete()` in `app/llm.py` (trace required, per-attempt timeout, retry loop with `Retry-After` and full jitter, 200-with-error handling, exact cost, one span per call). Verify with `tests/test_llm.py` against `httpx.MockTransport`, covering every llm-client scenario, including the API-key scan of stored rows.

## 4. Live check

- [x] 4.1 Register a `live` marker excluded by default, add `tests/test_llm_live.py`, and rewrite `scripts/hello_openrouter.py` as a traced call. Verify that `uv run pytest` skips it, that `uv run python -m scripts.hello_openrouter` prints a span id, and that the span row in the dev database has the model, tokens, cost, and status `ok`.

## 5. Integration

- [ ] 5.1 Run the full suite, lint, `alembic check`, and the spec-coverage check. Verify that all pass and every requirement in this change has a test with a matching `spec` marker.

## Workflow follow-up

- Archive the change after review, which merges the specs into `openspec/specs/`.
- Merge `phase-03-llm-tracing` into `main`.
