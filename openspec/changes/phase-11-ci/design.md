# Design

## Context

- **The model client** (`app/llm.py`) builds an `AsyncOpenAI` client over httpx. Tests already inject a custom httpx transport.
- **Demo samples** are processed as of 2027-03-03, and the seed builds data relative to any "today".
- **The comparison lab** already creates, migrates, and seeds a separate local database.
- **Tests write JUnit reports:** backend through pytest, frontend through Vitest. The walkthrough generator reads both.
- **No git remote exists yet,** so the pipeline is verified locally, step by step, until the repository is pushed.

## Goals / Non-Goals

**Goals:**
- CI that is deterministic, free, and needs no model key.
- The browser demo exercised automatically, not only by hand.
- A README that shows the system working.

**Non-Goals:** cloud deployment, CI performance tuning, recording responses in CI.

## Decisions

### D1. Recorded responses at the HTTP layer
Recorded in [decision record 0016](../../../docs/decisions/0016-recorded-model-responses-for-ci.md).
- `app/cassettes.py` has a `CassetteTransport` (an httpx transport):
  - the key is the SHA-256 of the exact request body, which holds the model, the messages (including image data), the tools, and the response format;
  - **record** forwards to the real network and saves the JSON body of each 200 response as `<key>.json`;
  - **replay** returns the saved body, or a 404 whose error names the key. A 404 is a permanent failure in the client, so it isn't retried.
- Settings `llm_cassette_mode` (`off` | `record` | `replay`) and `llm_cassette_dir` wire it into the default client. Everything above the transport (retries, spans, cost) runs unchanged, so replayed runs still produce full traces.
- Only response bodies are stored. Request bodies, which contain the images, and headers, which contain the key, are not.

### D2. End-to-end environment
- **`scripts/lab_database.py`:** `prepare(url, today)` creates, migrates, and seeds a local database. It's shared by the comparison lab and the end-to-end server.
- **`scripts/e2e_server.py`:**
  - points `DATABASE_URL` at `pawdesk_e2e`;
  - prepares it as of the demo day;
  - sets replay mode (or record mode when `PAWDESK_E2E_RECORD=1`) with `backend/tests/cassettes/e2e/`;
  - serves the API on port 8011.
- **Playwright's `webServer`** starts it and a Next.js dev server on port 3011 with `BACKEND_URL` set to the API.
- **Tests carry spec tags in their names** (decision record 0012). The JUnit report goes to `frontend/test-results/e2e-junit.xml`, and the walkthrough reads it as suite `e2e`.
- **The tests save screenshots** at each step. `scripts/make_demo_gif.py` (Pillow) assembles them into `docs/demo.gif`.

### D3. Pipeline (`.github/workflows/ci.yml`)
Triggered on `push` and `pull_request`. Jobs:

| Job | What it runs |
|---|---|
| `backend` | Postgres 18 service; uv; `ruff check`, `ruff format --check`; `alembic upgrade head`; `alembic check`; `pytest --junitxml` |
| `frontend` | pnpm; `lint`, `typecheck`, `test`, `build` |
| `e2e` | Postgres service; uv, pnpm, Playwright Chromium; `pnpm e2e` in replay mode |
| `traceability` | needs the three; downloads the JUnit artifacts; `walkthrough --check` |
| `secrets` | the gitleaks action over the full history |

- **Environment:** a placeholder `OPENROUTER_API_KEY` (settings require a value; replay never sends it) and a `DATABASE_URL` for the service container. No repository secrets are used.
- **A structural test** (`tests/test_ci_workflow.py`) reads the workflow and checks the triggers, the jobs, and that no step references a model key secret.

### D4. Secrets
- **`tests/test_secrets.py`** lists tracked files with `git ls-files` and fails on any value matching an OpenRouter key shape (`sk-or-v1-` followed by 40 or more hex characters), naming the file. The test fixtures' fake key isn't hex, by design.
- **gitleaks in CI** covers other key types and the history.

## Risks / Trade-offs

- [Recordings go stale when a prompt or schema changes] → Replay fails loudly with the missing key, and re-recording is one command. That's the point: CI then shows exactly which calls changed.
- [Replay proves the plumbing, not model quality] → Model quality is what the evals measure (decision record 0007), on demand.
- [The pipeline hasn't run on GitHub yet] → Every step was run locally, and the structural test guards the file.
