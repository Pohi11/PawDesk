# Tasks

## 1. Summaries

- [x] 1.1 Add `lib/step-summary.ts` with `stepSummary(id, status, detail)`. Verify with spec-tagged unit tests: every step's description, results for a clean run, an expired vaccine, no free kennel, a skipped resolver, a review by staff, waiting and running steps, and missing fields falling back to plain text.

## 2. Path

- [ ] 2.1 Give the path a custom step node (a button), the tooltip outside React Flow, and Escape to hide it, and pass the request detail from the run view. Verify with an end-to-end test that hovers and focuses a step on the clean sample's run, then lint, type check, and build.
- [ ] 2.2 Try it for real in a browser on runs with different outcomes. Verify with screenshots of the tooltip near the graph's edges and at phone width.

## 3. Integration

- [ ] 3.1 Run every suite and the coverage check, then regenerate the walkthrough.
