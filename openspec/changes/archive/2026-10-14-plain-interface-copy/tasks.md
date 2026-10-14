# Tasks

## 1. Rules and checks

- [x] 1.1 Add `docs/style/copy-rules.json` (the banned list from design D2), `docs/style/interface-copy.md` (the guide with PawDesk examples and the three exceptions), and decision record `docs/decisions/0018-plain-voice-for-interface-copy.md`. Verify the JSON parses and every link in the guide and the record resolves.
- [x] 1.2 Add `frontend/tests/copy.test.ts` (syntax-tree scan, design D3), with fixture tests for each scenario: a banned word reported with file, line, and word; `justify-self-end` ignored; an em dash in a sentence reported; a lone "—" allowed. Leave the "current dashboard passes" test marked as expected to fail until task 2.3. Verify with `pnpm test`, which runs the fixture tests and lists today's findings.

## 2. Rewrite

- [x] 2.1 Rewrite `outcome()` and `flagText()` in `lib/story.ts` (design D4), after confirming in `backend/app/orchestrator.py` that running a failed request again resumes from `failed_step`. Verify with `lib/story.test.ts`, tagged to "Outcome sentences name who decided" and "Failure sentences name the step in plain words", covering every row of the D4 table and a state missing from the map.
- [x] 2.2 Rewrite the demo sample titles and descriptions in `backend/app/demo.py`, and add `tests/test_demo_copy.py`, tagged to "Demo sample descriptions follow the same rules", which reads the shared list. Verify with `uv run pytest`, and with a temporary extra word in the list that makes both suites fail (scenario "One list for both checks").
- [x] 2.3 Rewrite the remaining dashboard copy page by page (design D5) and turn on the "current dashboard passes" test. Update `e2e/demo.spec.ts` to the new wording in the same commit. Verify with `pnpm test`, `pnpm lint`, `pnpm typecheck`, `pnpm build`, and `pnpm e2e`.

## 3. Integration

- [x] 3.1 Look at every page in a browser with seeded data and a finished demo run, and read the text on each one against the guide. Verify with screenshots of the home, Try, run, review, metrics, evals, and build pages.
- [x] 3.2 Regenerate `docs/demo.gif` from the new end-to-end frames, run every suite and the coverage check, and regenerate the build walkthrough. Verify with `uv run python -m scripts.make_demo_gif`, the full backend and frontend suites, and `--check` on the walkthrough.

## Workflow follow-up

- Archive the change and merge `plain-interface-copy` into `main`.
- Merge `main` into `demo-generated-requests` so the copy check covers its new Try page text.
