# 0014 — The build walkthrough is generated into a committed file

- **Date:** 2026-10-14
- **Status:** Accepted

## Context

The build walkthrough page shows how PawDesk was built: every archived change, every requirement with the tests that verify it and their latest result, and every decision record. All of it already exists as files: OpenSpec archives and specs, `docs/decisions/`, and the JUnit reports the test suites write. The page must stay truthful, so it has to come from those files rather than being written by hand. It must also read only public sources. The working agreement, the build plan, and the private notes must never leak into it.

The frontend's Docker image is built from `frontend/` alone, and the backend image doesn't ship `openspec/` or `docs/`.

## Options considered

1. **Hand-written page.** Simple, but it drifts, and nothing proves its claims.
2. **Generate during the frontend build** by reading `../openspec` and `../docs`. The data stays current, but it breaks the self-contained frontend build context and couples the build to the test reports.
3. **A backend endpoint that reads the repository at runtime.** The data is live, but the backend image would have to ship the specs, docs, and test reports, and a running service would be reading the repository.
4. **A generator script that writes a JSON file into the frontend, committed with the change.** The pages import it and are fully static.

## Decision

Option 4.
- **The generator:** `backend/scripts/walkthrough.py` reads an explicit list of sources:
  - the archived changes;
  - the current specs;
  - the decision records;
  - the backend and frontend JUnit reports.

  It writes `frontend/content/walkthrough.json`, with its generation time and the time of each test report.
- **`--check`** fails when any requirement lacks a passing linked test or a test names an unknown requirement. It replaces the one-off coverage script used at the end of earlier changes.
- **Ordering:** changes are ordered by the commit that archived them, because several can share a date.

## Consequences

- **Good:** Every statement on the page traces to a file, and the coverage claim ("106/106 verified") is checked by a command, not asserted.
- **Good:** The pages are static, cheap to serve, and independent of the backend.
- **Good:** A test proves that private notes never reach the output.
- **Cost:** The committed file can go stale between regenerations. The page shows when it was generated, and CI regenerates and checks it (Phase 11).
- **Cost:** Test results in the file are those of the last local run, not of CI, until CI takes over generation.
