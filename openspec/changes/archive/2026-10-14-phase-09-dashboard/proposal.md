# Proposal

## Why

PawDesk now makes real decisions with models in the loop. An operator can only trust that if they can see, for any request:
- what happened and in what order;
- what each model was asked and answered;
- what it cost, how long it took;
- why a request was stopped for review.

Everything needed is already recorded (traces, spans, step results, transitions, approvals). It is only visible through SQL today. The dashboard makes it visible live, and lets someone submit a request (including an injection attempt) and watch the system handle it.

## What Changes

- **Observability API (backend):**
  - list and inspect requests with their states, step results, transitions, and every span;
  - stream a run's progress as server-sent events;
  - metrics: cost per request and per model step, latency, flag rate, requests per state;
  - saved eval reports;
  - a demo endpoint that submits a sample request and processes it in the background.
- **Dashboard (frontend):**
  - **Requests** home with headline metrics.
  - **Live run view:**
    - a graph of the workflow whose nodes light up as steps run, colored by kind (model, code, tool, human);
    - a timeline waterfall where parallel steps visibly overlap;
    - a span inspector with the full input, output, tokens, cost, latency, and error.
  - **Review queue** with flag reasons and approve, edit, or reject.
  - **Metrics** charts and an **Evals** page.
  - **Demo panel** with sample requests, including an injection attempt.
- **The backend address stays server-side:** the browser talks only to a Next.js route that forwards an allowlisted set of API paths.
- **Frontend tests are linked to specs too,** with a decision record extending the traceability convention.

## Capabilities

### New Capabilities
- `observability-api`: Read-only HTTP access to requests, runs, spans, metrics, and eval reports, live progress as server-sent events, and demo submissions.
- `run-dashboard`: The operator dashboard: live run graph, timeline, span inspector, review queue, metrics, evals, and demo panel, served without exposing the backend to the browser.

### Modified Capabilities
None.

## Impact

- **Backend:**
  - new `app/observability.py` (queries and metrics) and routes in `app/api.py`;
  - new `app/demo.py` (sample requests).
- **Frontend:**
  - new pages under `frontend/app/`;
  - pure logic in `frontend/lib/` (graph status, timeline layout, proxy allowlist, formatting);
  - adds `@xyflow/react`, `recharts`, and `vitest`.
- **Tests:**
  - API tests against a real database;
  - frontend unit tests for the graph, timeline, and proxy logic, linked to specs;
  - a real demo run in a browser.
- **Out of scope:**
  - authentication (noted since Phase 8);
  - end-to-end browser tests in CI (Phase 11);
  - the build walkthrough page (Phase 9b).
