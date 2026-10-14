# Proposal

## Why

Every check so far runs on one developer machine, by hand:
- the backend suite against a real database;
- the frontend tests, lint, type check, and build;
- the spec-coverage check;
- the browser demo.

A change that breaks any of them is only caught if someone remembers to run it. Continuous integration runs all of them on every push and pull request.

Two of the checks need care in CI:
- **The end-to-end demo makes real model calls.** In CI those would cost money, need a secret, and give different answers from run to run, so CI must replay recorded responses instead.
- **CI must never be the way a secret leaks into the repository.**

The plan also calls for a README with an architecture diagram and a demo GIF, so a reader sees what the project does before reading any code.

## What Changes

- **Recorded model responses.** The model client can run in `record` mode (call the model and save each response under a hash of the exact request) or `replay` mode (answer only from saved responses and never touch the network). A request with no recording fails loudly.
- **End-to-end tests** (Playwright, against the real backend and dashboard on a fresh, seeded database, with replayed responses):
  - the clean demo sample runs live to `sent`;
  - the injection sample stops for review and is approved from the review queue to `sent`.
- **A secret check:**
  - a test fails if any tracked file contains something shaped like a real API key;
  - CI also runs a dedicated secret scanner over the history.
- **A GitHub Actions pipeline** with these jobs:
  - backend: lint, migrations, `alembic check`, tests against a Postgres service container;
  - frontend: lint, type check, unit tests, build;
  - end-to-end tests with replayed responses;
  - the walkthrough's coverage check over all three test reports;
  - the secret scan.
- **The walkthrough counts end-to-end tests** alongside backend and frontend tests.
- **The README** gains an architecture diagram, a demo GIF made from the end-to-end run's screenshots, the measured results, and how to run everything.
- **A decision record** for testing with recorded model responses.

## Capabilities

### New Capabilities
- `delivery-pipeline`: The CI pipeline, the end-to-end demo tests against replayed responses, and keeping secrets out of the repository.

### Modified Capabilities
- `llm-client`: adds recording and replaying model responses.
- `build-walkthrough`: end-to-end tests count as linked tests.

## Impact

- **Backend:**
  - new `app/cassettes.py`, wired into the client by settings;
  - new `scripts/lab_database.py` (shared by the comparison lab and the end-to-end server);
  - new `scripts/e2e_server.py` and `scripts/make_demo_gif.py`.
- **Frontend:**
  - new `e2e/` with Playwright and its config;
  - recorded responses are committed under `backend/tests/cassettes/e2e/`.
- **Repository:** new `.github/workflows/ci.yml`, and a rewritten `README.md`.
- **Out of scope:**
  - deploying to a cloud provider (optional in the plan; it needs credentials and is left for later);
  - running the pipeline on GitHub, which happens once the repository is pushed.
