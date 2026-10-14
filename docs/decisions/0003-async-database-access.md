# 0003 — Async database access with SQLAlchemy 2 and asyncpg

- **Date:** 2026-10-13
- **Status:** Accepted

## Context

PawDesk's orchestrator runs model calls concurrently with `asyncio` (intake and records extraction in parallel) and saves state to Postgres after every step. The API serves Server-Sent Events, which keep many connections open at once. Any database call that blocks the event loop stalls every in-flight run and stream.

Development happens on Windows hosts, where Python's default event loop is `ProactorEventLoop`. Production and Compose run on Linux.

## Options considered

1. **Sync SQLAlchemy, with calls offloaded to a thread pool.** Mature and simple, but every database call made from async code has to be wrapped. Forgetting once blocks the event loop without any visible error.
2. **Async SQLAlchemy with psycopg 3.** One driver for both sync and async code, but its async mode refuses `ProactorEventLoop`. That requires event-loop workarounds in tests, migrations, scripts, and the dev server on Windows.
3. **Async SQLAlchemy with asyncpg.** Async-only, the most widely used async driver with SQLAlchemy, and works on both Windows event loops.
4. **Raw asyncpg without an ORM.** Fastest, but gives up the unit of work, optimistic version checks, and Alembic autogenerate.

## Decision

Option 3. All application database access goes through SQLAlchemy 2's async engine with asyncpg (`postgresql+asyncpg://`), created in `app/db.py`. `.env` keeps a driver-neutral `postgresql://` URL, which `app/db.py` rewrites.

Rules that come with this choice:
- **Sessions use `expire_on_commit=False`.** In async code, reading an expired attribute would trigger an implicit query that can't run.
- **Relationships default to `lazy="raise"`.** Related rows are loaded explicitly (for example with `selectinload`), so a missing load fails in tests instead of failing at runtime.

## Consequences

- **Good:** Database work never blocks the event loop. The same code runs on Windows hosts and Linux containers with no event-loop configuration.
- **Good:** One access pattern for the API, the orchestrator, scripts, and tests.
- **Cost:** Two Postgres drivers are installed. psycopg remains for the synchronous `/health/db` probe.
- **Cost:** Async SQLAlchemy has sharp edges (implicit I/O, session lifetime across tasks). One `AsyncSession` must never be shared between concurrent tasks; each parallel step gets its own session.
