# Proposal

## Why

The run view's path shows nine steps with a status each ("Done", "Skipped", "Working"), but not what a step is for or what it found. A reader has to know the architecture already, or open the inspector and read raw JSON. The path should explain itself at a glance:
- **What the step does,** in one sentence, for someone seeing the desk for the first time.
- **What it found in this run,** in one line: what intake read, which vaccine failed, which kennel was free, who approved.

## What Changes

- **Hovering or focusing a step** in the path shows a tooltip with what the step does and, once it has run, a short summary of its result for this request.
- **Steps that haven't run, or were skipped,** say so and why, where the request shows it.
- **The summary is built from the request already loaded.** No new requests and no new API fields. It updates live with the run.
- **Steps become buttons:** keyboard users can tab to a step, read the same tooltip, and open it in the inspector with Enter.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `run-dashboard`: path steps show a tooltip explaining the step and its result in this run.

## Impact

- **Frontend:**
  - new `lib/step-summary.ts` (pure: step and request detail in, two sentences out);
  - `components/run-graph.tsx` gets a custom node and a tooltip;
  - `components/run-view.tsx` passes the request detail to the graph.
- **Backend:** none.
- **Tests:**
  - unit tests for every step's summary across the run's outcomes;
  - an end-to-end test that hovers and focuses a step on a real run view.
