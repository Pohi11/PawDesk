# Tasks

## 1. Observability API

- [x] 1.1 Add `app/observability.py` (request list and detail, metrics, eval reports) and their routes. Verify with `tests/test_observability_api.py`: list with cost and flag, whole-run detail, 404, cost per step, flag rate, reports listed.
- [x] 1.2 Add the server-sent events stream. Verify with tests for progress then end, and for a resting request.
- [x] 1.3 Add demo samples and background submission with an injectable model client. Verify with tests for submitting the injection sample (processed to review with a scripted model) and an unknown sample (404, nothing stored).

## 2. Dashboard

- [x] 2.1 Add vitest with JUnit output and the `specTest` helper, `@xyflow/react`, and `recharts`. Write [decision record 0012](../../../../docs/decisions/0012-frontend-test-traceability.md). Verify `pnpm test` writes a JUnit report with spec-tagged names.
- [x] 2.2 Add the allowlisted proxy route (`lib/proxy.ts` + `app/api/[...path]/route.ts`). Verify with unit tests for allowed and refused paths, streaming pass-through, and no backend call for refused paths. (The check that no client component reads the backend address lands with the components in 2.4.)
- [x] 2.3 Add `lib/graph.ts`, `lib/timeline.ts`, and `lib/format.ts`. Verify with unit tests for: parallel running nodes, skipped resolver, waiting for review, overlapping bars, nesting depth, and inspector formatting.
- [x] 2.4 Build the pages: home, live run view (graph, timeline, inspector, SSE), review queue, metrics, evals, demo. Verify that `pnpm lint`, `tsc`, and `pnpm build` pass.

## 3. Decision and real run

- [x] 3.1 Write [decision record 0013](../../../../docs/decisions/0013-live-updates-sse-from-database.md). Verify it exists and that design D1 links to it.
- [x] 3.2 Real demo in a browser: submit the clean and injection samples from the demo page, watch both live, approve the flagged one from the review page. Verify with screenshots and by recording the outcomes.

## 4. Integration

- [x] 4.1 Run the backend suite, the frontend tests, lint, type check, build, `alembic check`, and the spec-coverage check over both JUnit reports. Verify all pass and every requirement in this change has a linked test.
