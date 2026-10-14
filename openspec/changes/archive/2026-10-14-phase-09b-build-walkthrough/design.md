# Design

## Context

- **Archived changes** live in `openspec/changes/archive/<date>-<name>/` with `proposal.md`, `design.md`, `tasks.md`, and spec deltas under `specs/<capability>/spec.md`.
- **Current requirements** are in `openspec/specs/<capability>/spec.md`.
- **Decision records** are `docs/decisions/NNNN-<title>.md`.
- **Tests link to requirements in two ways:**
  - backend tests carry a `spec` property in pytest's JUnit XML (decision record 0004);
  - frontend tests carry `[spec <capability>: <requirement>]` in their names (decision record 0012).
- **The frontend Docker image is built from `frontend/` alone,** so it can't read the repository at build time.

## Goals / Non-Goals

**Goals:**
- Every claim on the page traces back to a file in the repository.
- Coverage gaps become a failing command instead of something to remember.
- The page shows the method (changes, specs, tests, decisions), not authorship.

**Non-Goals:** git history views, editing from the page, live test runs.

## Decisions

### D1. Generate into a committed JSON file
Recorded in [decision record 0014](../../../../docs/decisions/0014-walkthrough-generated-into-a-committed-file.md).
- `uv run python -m scripts.walkthrough` (from `backend/`) writes `frontend/content/walkthrough.json`. The pages import it and are fully static.
- *Alternatives:*
  - generating during the frontend build (the build context is `frontend/` only);
  - a backend endpoint (the backend image doesn't ship `openspec/` or `docs/`).

### D2. Sources, and only those
- **`SOURCES`:** the generator reads from `openspec/changes/archive/`, `openspec/specs/`, `docs/decisions/`, and the two JUnit paths it is given. It doesn't walk the repository.
- **Private files** (`CLAUDE.md`, `PLAN.md`, `docs/private/`) are never opened. A test plants a marker in a private file of a synthetic repository and checks that it never reaches the output.

### D3. Parsing
- **Changes:**
  - the folder name gives the date and the slug;
  - the title is humanized from the slug;
  - from `proposal.md`: the `## Why` text and the `## What Changes` markdown;
  - from `tasks.md`: sections and `- [x]` items;
  - from the spec deltas: `### Requirement:` names under `## ADDED|MODIFIED|REMOVED|RENAMED Requirements`;
  - decision references: `decisions/(\d{4})-` in proposal, design, and tasks.
- **Specs:** the capability, its `## Purpose`, and each requirement's text and scenarios (`#### Scenario:` blocks with their WHEN/THEN lines).
- **Decisions:** the number and title from `# NNNN — Title`, the date and status from the header bullets, and the full markdown.
- **JUnit:**
  - each `testcase` gives its suite (backend or frontend), id (`classname::name`), status (`failed` if it has failure or error, `skipped` if it has skipped, else `passed`), and time;
  - the testsuite `timestamp` is kept as the report time;
  - backend links come from `property name="spec"`, frontend links from the name tag.

### D4. Check mode
`--check` prints:
- each requirement that isn't `verified`;
- each link naming an unknown requirement.

It exits 1 if there are any, and 0 otherwise. This replaces the one-off coverage script used at the end of earlier changes.

### D5. Pages (`frontend/app/build/`)
| Page | Content |
|---|---|
| `/build` | methodology, totals (changes, requirements verified, tests, decisions), and the change timeline |
| `/build/specs` | the spec browser, grouped by capability. Each requirement has the anchor `req-<capability>-<slug>`, its status, its scenarios, and its tests with their results. |
| `/build/decisions` | each decision under the anchor `adr-NNNN`, rendered with `react-markdown` |

`lib/walkthrough.ts` holds the anchor and link helpers, which are pure and unit-tested.

## Risks / Trade-offs

- [The committed JSON can go stale] → It records its generation time and the report times, which the page shows. Phase 11 regenerates it in CI.
- [Hand-parsing markdown] → The formats are produced by one workflow and validated by `openspec validate`. The parser is tested on a synthetic repository.
