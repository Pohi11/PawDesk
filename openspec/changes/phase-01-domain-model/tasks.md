# Tasks

## 1. Database access layer

- [x] 1.1 Add `sqlalchemy[asyncio]`, `alembic`, and `pytest-asyncio` to the backend. Verify with `uv sync` and `uv run python -c "import sqlalchemy, alembic"`.
- [x] 1.2 Add `app/db.py`: an async engine and session factory built from `DATABASE_URL`, rewriting the scheme to `postgresql+psycopg://`. Verify with `tests/test_db.py::test_engine_executes_select_1`.
- [x] 1.3 Write [decision record 0003](../../../docs/decisions/0003-async-database-access.md) (async database access). Verify the file exists and that design D1 links to it.

## 2. Test infrastructure and traceability

- [x] 2.1 Add the `pawdesk_test` database fixture. It creates the database if missing, runs `alembic downgrade base` then `alembic upgrade head`, and gives each test a session inside a transaction that is rolled back afterward. Verify with `tests/test_isolation.py`: a row committed in one test is absent in the next.
- [x] 2.2 Register the `spec(capability, requirement)` pytest marker and add a `conftest.py` hook that writes it into JUnit XML properties. Verify that `uv run pytest --junitxml=…` output contains the marker properties for a marked test.
- [x] 2.3 Write [decision record 0004](../../../docs/decisions/0004-spec-test-traceability.md) (spec-to-test traceability). Verify the file exists and that design D13 links to it.

## 3. Booking domain schema

- [x] 3.1 Add `app/enums.py` (Species, Service, SizeClass, plus later enums) and ORM models for facilities, owners, pets, vaccine rules, vaccine records, kennels, and reservations. Verify with `uv run ruff check` and that the models import.
- [x] 3.2 Initialize Alembic with the async template and write the first migration: the `btree_gist` extension, all booking-domain tables, the generated `size_class` column, the reservation exclusion constraint, and every CHECK and unique constraint. Verify that a fresh test session runs the downgrade/upgrade round trip.
- [x] 3.3 Add the facility time-zone validator. Verify with `tests/test_booking_domain.py`, covering every booking-domain scenario (owner/species/weight rejection, size-class boundaries and recompute, invalid time zone, per-service rules, duplicate rule, vaccine record dates, kennel size class, overlap/back-to-back/different-kennel/zero-night reservations, one reservation per request).

## 4. Lifecycle guard

- [x] 4.1 Write `tests/test_lifecycle_guard.py`. It enumerates the allowed set from the spec and parametrizes over **every** (from, to, actor) combination, asserting that allowed ones pass and all others raise `IllegalTransition` naming both states. It also covers retry to the recorded failed step versus a different step, `sent` being terminal, and both paths into `approved`. Verify that it collects and fails, since the guard doesn't exist yet.
- [x] 4.2 Implement `app/lifecycle.py`: the `State` and `Actor` enums, the allowed-transition table, and the guard function, with no I/O. Verify that `tests/test_lifecycle_guard.py` passes in full.

## 5. Booking requests and the transition service

- [x] 5.1 Add models and a migration for booking requests (status, `failed_step`, `last_error`, `version`), the transition log, and approvals, including the failed-state CHECK and the reject-requires-reason CHECK. Verify the round trip and `tests/test_booking_lifecycle.py::test_new_request_starts_received` / `test_unknown_state_rejected`.
- [x] 5.2 Implement `app/transitions.py`: `transition()` applies the guard, updates the state, sets or clears the failure fields, appends the log row, and flushes, converting `StaleDataError` into `TransitionConflict`. Verify with `tests/test_booking_lifecycle.py`, covering the logged transition, no log entry on rejection, failure recorded, retry clearing the failure, staff rejecting a failed request, the stale update rejected with exactly one log row, and reject-without-reason rejected.

## 6. Run tracing schema

- [x] 6.1 Add models and a migration for traces and spans: kind and status CHECKs, error-requires-message, non-negative tokens and cost, `ended_at >= started_at`, `NUMERIC(14,10)` cost, `JSONB` payloads, and the composite parent foreign key. Verify with `tests/test_run_tracing.py`, covering every run-tracing scenario, including the 8-decimal cost round trip and the cross-trace parent rejection.

## 7. Seed data

- [x] 7.1 Implement `scripts/seed.py`: the host allowlist, a single `TRUNCATE … CASCADE`, and the fixed fictional dataset with dates relative to today, all in one transaction. Verify with `tests/test_seed.py`, covering every table populated, all five kennel size classes, the three vaccine edge cases, identical counts after two runs, and a non-local host refused with no changes.
- [x] 7.2 Run the seed against the development database. Verify with `uv run python -m scripts.seed`, which prints per-table counts.

## 8. Integration

- [x] 8.1 Make the backend container run `alembic upgrade head` before uvicorn. Verify that `docker compose up --build` reports all services healthy and `/health/db` returns ok.
- [x] 8.2 Update `README.md` with the migrate, seed, and test commands. Verify that each documented command runs as written.
- [x] 8.3 Run the full suite and lint. Verify that `uv run pytest` and `uv run ruff check . && uv run ruff format --check .` pass, and that every spec requirement in this change has at least one test carrying a matching `spec` marker.

## Workflow follow-up

- Archive the change after review, which merges the specs into `openspec/specs/`.
- Merge `phase-01-domain-model` into `main`.
