# Tasks

## 1. Storage

- [x] 1.1 Add the `booking_documents` and `booking_step_results` models and a migration, plus `attach_certificate()` with magic-byte and size checks. Verify with `tests/test_orchestration_storage.py`, covering image round-trip with hash, type and size, a second certificate rejected, a PDF refused, and a duplicate step result rejected.

## 2. Orchestrator

- [x] 2.1 Implement `process_request()` in `app/orchestrator.py`: the received → extracting checkpoint, concurrent extraction with no session held during the model calls, checks (pet cross-check, compliance with on-file plus extracted records, capacity for boarding), routing with reasons, and saved results with transitions in one transaction. Verify with `tests/test_orchestrator.py` against scripted model answers, covering concurrency, no certificate, every check scenario, every routing scenario, and tracing.
- [ ] 2.2 Add resume and failure behavior: skip steps that have saved results, the crash hook, failures moving to `failed`, retrying from the failed step, and finished requests left unchanged. Verify with the crash-after-extraction (no model calls on resume), crash-during-extraction (exactly one result per step), finished-request, failure, and retry tests.
- [ ] 2.3 Close abandoned spans when processing starts. Verify with tests for a span left running being closed as abandoned, and for finished spans being left untouched.

## 3. Decisions

- [ ] 3.1 Write [decision record 0008](../../../docs/decisions/0008-hybrid-workflow-over-agentic.md) (hybrid workflow over agentic) and [decision record 0009](../../../docs/decisions/0009-durable-execution-with-step-checkpoints.md) (durable execution). Verify both exist and that design D1/D2 link to them.

## 4. Command line and real runs

- [ ] 4.1 Add `scripts/bookings.py` with `submit`, `process`, and `resume` (with an optional `--crash-after STEP` hard stop). Verify with a test of `submit` storing the request and certificate.
- [ ] 4.2 Real end-to-end: submit a seeded owner's message with a benchmark v2 certificate, process it, and confirm routing. Then a real kill: submit another, `process --crash-after extracting`, `resume`, and confirm it completes without new extraction model calls (span counts). Verify by recording the observed states and span counts.

## 5. Integration

- [ ] 5.1 Run the full suite, lint, `alembic check`, and the spec-coverage check. Verify that all pass and every requirement in this change has a test with a matching `spec` marker.

## Workflow follow-up

- Archive the change after review, which merges the specs into `openspec/specs/`.
- Merge `phase-06-orchestrator` into `main`.
