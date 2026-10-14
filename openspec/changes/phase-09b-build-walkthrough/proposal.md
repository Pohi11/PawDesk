# Proposal

## Why

A finished project says little about how it was built. Claims like "spec-driven" or "fully tested" are easy to write and hard to check. The repository already holds the evidence:
- every change, archived with its proposal, design, and tasks;
- every requirement, with WHEN/THEN scenarios;
- every decision record;
- tests that each name the requirement they verify.

A reviewer should be able to follow that evidence without reading the repository: from a change to the requirements it added, from a requirement to the tests that verify it and their latest result, and from a change to the decisions it relied on. Generating the page from those files, instead of writing it by hand, keeps it honest.

The coverage check run at the end of every change has so far been a one-off script. The generator makes it part of the project.

## What Changes

- **A generator** (`backend/scripts/walkthrough.py`) reads only the public sources:
  - the archived changes;
  - the current specs;
  - the decision records;
  - the backend and frontend JUnit reports.

  It writes `frontend/content/walkthrough.json`. Its `--check` mode fails when a requirement has no passing linked test, or a test names a requirement that doesn't exist.
- **The build walkthrough pages,** separate from the runtime dashboard:
  - **methodology and change timeline:** each archived change with its date, motivation, what changed, tasks, the requirements it added or changed, and the decisions it relied on;
  - **spec browser:** each requirement with its scenarios, its linked backend and frontend tests, and their latest result;
  - **decisions:** every decision record, rendered in full.
- **A decision record** for generating the page into a committed file.

## Capabilities

### New Capabilities
- `build-walkthrough`: Generating the build walkthrough from the repository's public sources, linking changes, requirements, tests, results, and decisions, checking spec coverage, and presenting it as pages that describe the methodology.

### Modified Capabilities
None.

## Impact

- **Backend:** new `scripts/walkthrough.py`. Pytest writes its JUnit report to `backend/test-results/` (ignored by git).
- **Frontend:**
  - new pages under `app/build/`;
  - helpers in `lib/walkthrough.ts`;
  - adds `react-markdown` to render decision records;
  - the committed `content/walkthrough.json`.
- **Tests:**
  - the generator against a small synthetic repository (including a private file it must not read);
  - the check mode's failures;
  - the frontend link helpers;
  - the real pages in a browser.
- **Out of scope:**
  - regenerating the file in CI (Phase 11);
  - git history views.
