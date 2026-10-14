# Proposal

## Why

Every later step (compliance checks, capacity checks, agents, approvals, and the dashboard) reads and writes the same core records: owners, pets, vaccine rules, kennels, reservations, and booking requests. A booking request also has to move through a strict lifecycle. A single `approved` flag can't tell "not checked yet" apart from "rejected" or "crashed halfway," and it can't stop untrusted input from jumping straight to approval. The domain model and lifecycle have to exist, and be enforced by the database and plain code, before any LLM step is added.

## What Changes

- Add a PostgreSQL schema, managed by versioned migrations, for: owners, pets, facilities, vaccine rules, vaccine records, kennels, reservations, booking requests, booking-request transitions, approvals, traces, and spans.
- Derive a pet's size class from its species and weight using fixed thresholds.
- Make the database itself reject overlapping reservations for the same kennel.
- Add a booking-request lifecycle with an explicit table of allowed transitions, including a `failed` state that records which step failed and why. Retry returns the request to that step.
- Restrict entry into `approved` to two paths only: the system, from `ready` (all deterministic checks clear), or staff, from `needs_review`.
- Record every transition in an append-only transition log.
- Detect concurrent updates to the same booking request and reject the stale one.
- Add a seed command that loads a synthetic dataset into a development database, and that can safely be run more than once.
- Add a test convention that links each test to the spec requirement it verifies.

## Capabilities

### New Capabilities
- `booking-domain`: The records a facility needs to decide on a booking (owners, pets and their size class, facilities, per-service vaccine rules, vaccine records, kennels, reservations) and the invariants on them.
- `booking-lifecycle`: The states a booking request moves through, who may trigger each transition, failure and retry, the transition audit log, staff approval records, and protection against concurrent updates.
- `run-tracing`: Storage for traces and spans, so every step of a run can be recorded with timing, token usage, cost, and errors.
- `seed-data`: A repeatable synthetic dataset for development and demos.

### Modified Capabilities

None. This is the first change with spec-level behavior.

## Impact

- **Backend:** New dependencies: SQLAlchemy 2 (async), Alembic, and an async pytest plugin. New modules for the ORM models, the lifecycle guard and transition service, a seed command, and Alembic migrations.
- **Database:** Postgres 18 with the `btree_gist` extension (needed for the reservation-overlap constraint). Primary keys use Postgres 18's built-in `uuidv7()`.
- **Tests:** A separate test database, created and migrated automatically. Tests now run against a real Postgres schema.
- **Out of scope:** HTTP endpoints for these records, the compliance and capacity logic (Phase 2), step orchestration and crash resume (Phase 6), and pet-parent cancellation.
