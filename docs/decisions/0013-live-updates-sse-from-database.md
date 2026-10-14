# 0013 — Live run updates are server-sent events fed by reading the database

- **Date:** 2026-10-14
- **Status:** Accepted

## Context

The dashboard's run view should light up steps as they happen, while a demo request is being processed or a staff action resumes a run. Runs are processed by more than one process: the API (demo submissions and staff actions, as background work) and the command line (`scripts/bookings.py`). Every process records its progress the same way, as spans written and committed while work runs (decision record 0006), plus state changes. The browser also never talks to the backend directly. Its requests go through the dashboard's allowlisted proxy route.

## Options considered

1. **Client polling.** The browser re-fetches the whole request every second. Simple, but every viewer pulls full payloads, and an update arrives up to a full interval late.
2. **WebSockets.** Two-way and low-latency, but the traffic only flows one way. A WebSocket also can't pass through an ordinary HTTP route handler, and it needs its own reconnect logic.
3. **Server-sent events, fed by an in-process event bus.** Push without polling. But it only sees runs in the same process, so a command-line run would be invisible.
4. **Server-sent events, fed by reading the database.** The stream reads a light snapshot (state, plus each span's timing and status) every half second, and sends it only when it changed.
5. **Server-sent events, fed by Postgres LISTEN/NOTIFY.** Push from every process with low latency, but every writer (or a trigger) must notify, which adds moving parts to the tracing path.

## Decision

Option 4.
- **The endpoint:** `GET /requests/{id}/events` is a `text/event-stream`.
  - **What it sends:** a snapshot when the stream opens and whenever the snapshot changes.
  - **When it ends:** once the request is resting (`sent`, `needs_review`, `failed`) with no span running, or after five minutes.
- **The proxy** passes the response body through as a stream.
- **The browser** uses `EventSource`. It reconnects on its own, and the view closes it when the page is hidden.
- **On each snapshot,** the view re-fetches the full request for the inspector. The snapshot itself stays small.

## Consequences

- **Good:** It works for runs from any process, because the database is the one place they all write to.
- **Good:** One-way HTTP that passes through the existing proxy and its allowlist, with nothing new to run.
- **Cost:** A light query per open stream every half second, and up to half a second of delay. Fine for a handful of operators. LISTEN/NOTIFY is the upgrade path if viewers or latency demands grow.
- **Cost:** The stream doesn't resume after it ends. After a staff action, the view reloads to follow the rest of the run.
