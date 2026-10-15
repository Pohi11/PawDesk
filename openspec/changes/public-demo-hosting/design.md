# Design

## Context

- **Locally,** the stack is three containers (decision record 0002): Postgres, the FastAPI backend, and the Next.js dashboard. The browser reaches the backend only through the dashboard's allowlisted proxy (`app/api/[...path]/route.ts`).
- **The chosen hosts** (decision record 0019): a Hugging Face Docker Space runs one container with one public port, and its disk is wiped on every restart. Neon provides the Postgres database outside the container.
- **The only route that calls the model** is `POST /demo/requests`. Staff actions resume a run from a decision and make no model call. Every model call is already recorded as a span of kind `llm` (decision record 0006).

## Goals / Non-Goals

**Goals:**
- anyone with the link can use every page;
- the model bill has a hard ceiling;
- the hosted database starts each boot in the seeded demo state;
- nothing private can reach the Space.

**Non-Goals:**
- sign-in for staff (everyone who opens the demo acts as staff; see D6);
- per-visitor fairness;
- more than one backend process.

## Decisions

### D1. One container, two processes
- **The image** builds the dashboard in a Node stage and the backend's environment in a Python stage. The runtime image is `python:3.12-slim` with the `node` binary copied in, which is all Next's standalone server needs.
- **`start.sh`** runs `alembic upgrade head`, then the seed (D4), then starts uvicorn on `127.0.0.1:8000` and the dashboard on `0.0.0.0:$PORT` (7860).
- **The backend stays private.** It listens on the loopback address only, so the allowlisted proxy is still the only way in, as it is locally.
- **If either process exits, the container exits** (`wait -n`), and the Space restarts it. A half-running container that serves pages with no API would be worse.

### D2. Neon's direct endpoint, not the pooler
- **asyncpg uses prepared statements,** which need care behind PgBouncer in transaction mode. With one backend process and a small pool, connection pooling buys nothing here.
- **The URL Neon gives** carries `sslmode=require&channel_binding=require`. `async_url` translates `sslmode` into asyncpg's `ssl` and drops `channel_binding` (asyncpg doesn't support it, and TLS is still required). psycopg, used by `/health/db`, takes the URL as given.

### D3. Limits counted from recorded model calls
- **What is counted:** spans of kind `llm` started in the last hour and the last 24 hours. That is exactly what costs money, it survives restarts, and it needs no new table. Seeded data has no spans, so a reseed doesn't use up the limit.
- **Where it is checked:** at the start of `POST /demo/requests`, before anything is stored. A refused request leaves no trace.
- **Overshoot is bounded:** runs already in flight finish, so a limit can be passed by the calls of the runs that were accepted just before it was reached (a handful of calls each).
- **Settings:** `DEMO_MODEL_CALLS_PER_HOUR` and `DEMO_MODEL_CALLS_PER_DAY`, unset by default.
- **Rejected: per-visitor limits by IP.** The client address passes through Hugging Face's proxy and then the dashboard's proxy, so it would need trusted forwarding headers. A global ceiling bounds the cost, which is the actual risk.
- **Second line of defence:** the Space uses its own OpenRouter key with a credit limit set at OpenRouter, so a bug in the check can't spend more than that limit.

### D4. Reseed on every start, for one named host
- **The demo resets itself.** The Space sleeps when idle and restarts on every deploy, so each boot starts from the known synthetic dataset and leftovers from strangers don't accumulate.
- **Naming the host, not a yes/no switch.** `PAWDESK_SEED_ALLOWED_HOST` must equal the database's host exactly. A boolean would also allow wiping whatever database a mistyped `DATABASE_URL` points at.

### D5. Deploy from `git archive HEAD`
- **The bundle is built from the commit,** not the working tree, so `.env`, ignored files, and private notes can't be included by construction.
- **The Space's Dockerfile and README** (in `deploy/huggingface/`) are copied to the bundle's root. Hugging Face reads a Space's settings from the README's front matter, so the Space README replaces the repository's.
- **Upload with `hf upload`**, which commits the bundle to the Space's repository and starts a build. Secrets are set on the Space, never in the bundle.

### D6. Everyone is staff in the public demo
- **No sign-in.** Every visitor can approve, edit, or decline replies in the review queue, because trying that is part of the demo.
- **It is safe here because:** all data is synthetic, a "sent" reply is a state change with no email or message behind it, and the data resets on every start (D4).
- **Real sign-in is still needed** before any real business data is involved.

## Risks / Trade-offs

- [Neon's compute sleeps when idle] → The first request after a pause waits for it to wake (`pool_pre_ping` covers stale connections).
- [The dashboard's live views poll the database twice a second] → Only while someone is watching a run, and the Space sleeps after two idle days.
- [A visitor changes the data others see] → Accepted for a demo (D6); it resets on the next start.
- [The Space's free hardware is shared and can be slow to build] → The image reuses the existing frozen lockfiles, so builds are reproducible.
