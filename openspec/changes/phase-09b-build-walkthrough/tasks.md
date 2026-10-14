# Tasks

## 1. Generator

- [ ] 1.1 Implement `scripts/walkthrough.py`: parse archived changes, specs, decisions, and both JUnit reports from the listed sources only, and write the JSON. Verify with `tests/test_walkthrough.py` against a synthetic repository: every change in date order with tasks and requirement deltas, private marker absent, verified, failing, and untested requirements, decision links.
- [ ] 1.2 Add `--check`. Verify with tests for a gap (untested, unknown name) exiting 1 and for complete coverage exiting 0.

## 2. Pages

- [ ] 2.1 Add `lib/walkthrough.ts` (anchors and links) with unit tests for stable, distinct anchors and change-to-requirement links. Add `react-markdown`, then build `/build`, `/build/specs`, and `/build/decisions`, plus a nav link. Verify that lint, the type check, the tests, and the build pass.

## 3. Decision and real data

- [ ] 3.1 Write [decision record 0014](../../../docs/decisions/0014-walkthrough-generated-into-a-committed-file.md). Verify it exists and that design D1 links to it.
- [ ] 3.2 Generate the real `walkthrough.json` from fresh test reports, run `--check`, and verify in a browser that every archived change is on the timeline and that following a requirement reaches its tests and results.

## 4. Integration

- [ ] 4.1 Run the backend suite, the frontend tests, lint, type check, build, and `--check` (which now replaces the one-off coverage script). Verify all pass.
