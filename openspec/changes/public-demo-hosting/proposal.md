# Proposal

## Why

The demo runs only on a developer machine. A reviewer who wants to try it has to clone the repo, start Postgres, and bring their own model key. A hosted copy lets anyone open a link and send a request.

Hosting it publicly changes three things:
- **Anyone can make model calls.** Each sent request costs money on the project's model key, and nothing limits how many a stranger sends.
- **The database is not local any more.** The seed command refuses every non-local host (on purpose: it deletes everything), so the hosted database can't be reset to the known demo state.
- **Hosted Postgres URLs carry libpq options.** Neon's connection string ends in `?sslmode=require&channel_binding=require`. psycopg accepts those, but SQLAlchemy passes query options straight to asyncpg as keyword arguments, and asyncpg rejects both, so the backend can't connect.

The hosting choice itself (Hugging Face Spaces for the app, Neon for Postgres) is recorded in decision record 0019.

## What Changes

- **Model use is capped.** Optional hourly and daily limits on model calls, counted from the trace spans the system already records. When either is reached, sending a demo request answers 429 with a plain explanation and stores nothing. No limits are set by default, so local development and tests are unchanged.
- **The Try page explains a reached limit** with the server's explanation, instead of asking whether the API is running.
- **Hosted Postgres URLs work as given.** The async URL translation turns `sslmode` into asyncpg's `ssl` and drops `channel_binding`, which asyncpg doesn't support.
- **The seed command can reset one named remote host.** A remote host is still refused unless it is exactly the host named in `PAWDESK_SEED_ALLOWED_HOST`.
- **A single-container image for the Space.** It builds the dashboard and the backend, and on start runs migrations, reseeds the demo data, serves the backend on `127.0.0.1:8000`, and serves the dashboard on the Space's public port.
- **A deploy script** that uploads only files committed at `HEAD`, plus the Space's own Dockerfile and README.

## Capabilities

### New Capabilities
- `demo-hosting`: model-use limits, the limit message, hosted database URLs, and what a deploy publishes.

### Modified Capabilities
- `seed-data`: a remote host can be reset when it is named explicitly.

## Impact

- **Backend:** `app/config.py` (limit and seed-host settings), `app/db.py` (URL translation), `app/api.py` (limit check on demo submissions), `scripts/seed.py` (named remote host).
- **Frontend:** `lib/demo.ts` and the demo panel show the limit message.
- **Deployment:** `deploy/huggingface/` (Dockerfile, start script, Space README, deploy script).
- **Docs:** decision record 0019; README section on the hosted demo.
