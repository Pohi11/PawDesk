# Proposal

## Why

The dashboard's copy reads as templated. It leans on stock patterns: slogans built on a contrast ("Models are measured, not trusted"), three-part runs ("The same requests, the same model, and the same checking tools"), filler adverbs ("exactly"), and passive sentences that hide who acted ("Every request so far was decided by the checks").

The passive voice costs more than style here. The desk's main safety property is who approves a booking: the checks or a named person, never a model. A sentence like "A polite decline was sent" leaves the reader to work out who decided.

Two strings also state things that are false:
- The build page says "Nothing on these pages is written by hand," but its method section is hand-written.
- A failed send reads "Stopped while approved," which shows a raw state name.

## What Changes

- **Rewrite the dashboard's interface copy** in a plain voice:
  - every page intro, heading, label, empty state, and status sentence;
  - the demo samples' titles and descriptions, which the backend serves to the Try page.
- **Name the actor** in each sentence that reports a decision: the checks, or the staff member by name.
- **Fix the two false strings.**
- **Add a copy check** that fails the build on the parts of the rules a program can verify:
  - a shared list of banned words and phrases;
  - no em dash inside a sentence.
- **Add a short public style guide** for the rules that need judgment, and a decision record for adopting it.
- **Update the end-to-end test and the demo GIF** to the new wording.

## Capabilities

### New Capabilities
- `interface-copy`: The rules the dashboard's user-facing text follows, and how the build checks them: banned words, punctuation, and sentences that name who decided.

### Modified Capabilities
None. The run-dashboard requirements describe behavior, not wording, and stay as they are.

## Impact

- **Frontend:**
  - copy in `app/`, `components/`, `lib/story.ts`, and `lib/comparison.ts`;
  - a new copy check in `tests/`;
  - updated unit tests for `lib/story.ts`;
  - `e2e/demo.spec.ts`.
- **Backend:**
  - sample titles and descriptions in `app/demo.py`;
  - a test that runs the same banned list over them.
- **Docs:**
  - `docs/style/interface-copy.md` (the guide);
  - `docs/style/copy-rules.json` (the list both checks read);
  - decision record 0018;
  - a regenerated `docs/demo.gif` and build walkthrough.
- **Not touched:** specs, decision records, and generated walkthrough content keep their own text. Routing reasons from the backend stay as they are.
