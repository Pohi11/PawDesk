# Tasks

## 1. Sample-card measurement (before the prompt changes)

- [x] 1.1 Add the pure scoring to `scripts/eval_sample_cards.py`: misread, decision flip (card records alone, sample stay), silent flip, and per-card and total counts. Verify with `tests/test_eval_sample_cards.py`, tagged `@spec("certificate-evaluation", "Sample cards are read repeatedly to measure misreads")` and covering the shifted-year, exact-read, decision-flip, and silent-flip scenarios.
- [x] 1.2 Add the runner: N reads per card (default 20) through `run_records` with `today=DEMO_TODAY`, the sample's pet as the booked pet, and truth from `draw_sample_cards.CARDS`. It is traced like `eval_records`, and the report records the prompt version, model, reads per card, and total cost. Verify the report-building test for the "Report names what it measured" scenario passes, and that `uv run python -m scripts.eval_sample_cards --help` (or a dry import) runs without calling the model.
- [x] 1.3 Run the measurement live on `records-v1` and commit the report to `evals/results/` unedited. Verify the report file exists and names `records-v1`.

## 2. Records prompt keeps printed years

- [ ] 2.1 Add the copy-dates-as-printed wording to `app/prompts/records.py` and set `PROMPT_VERSION = "records-v2"` (design D1). Verify with a prompt test tagged `@spec("vaccine-records-extraction", "Printed dates are copied exactly")` for the "Prompt keeps printed years" scenario, plus a span test that the `records` span records `records-v2`.
- [ ] 2.2 Run the sample-card measurement again on `records-v2` and commit its report. Verify the report names `records-v2`, and compare the misread, flip, and silent-flip counts with the 1.3 report.
- [ ] 2.3 Run `uv run python -m scripts.eval_records v2` on `records-v2` and commit its report. Verify the report names benchmark `v2` and prompt `records-v2`, and compare given accuracy, expiry accuracy, and silent disagreements with `records-v2-20261014T155439Z.json`.

## 3. Seed anchored to the demo day

- [x] 3.1 Make the seed command pass `DEMO_TODAY` as the anchor (design D4), and update the module docstring. Verify with tests tagged `@spec("seed-data", "Seeded dates are anchored to the demo day")`: the arguments are read with the demo day as the anchor, and Biscuit's Bordetella on file is at -60/+120 days from it.
- [x] 3.2 Move Moose's Bordetella on file to the dates on his card, his seeded large-kennel stay to days +21 to +28, and his rabies expiry to day +24 (design D5). Update `tests/test_compliance_db.py` to check his stay on the new days. Verify the full backend suite passes, including the existing seed edge-case tests.
- [x] 3.3 Add the sample-promise test (design D6), tagged `@spec("observability-api", "Samples end as promised from seeded and printed records")`, with one test per scenario: clean, injection, expired-vaccine only on Bordetella, and clean on records on file alone. Verify it passes. Also verify that it fails when the 3.2 Moose edit is reverted locally.

## 4. Recordings and end-to-end

- [ ] 4.1 Record the end-to-end model responses again (`PAWDESK_E2E_RECORD=1 pnpm e2e`, with that worktree's own test database). Remove recordings that are no longer used. Verify that `pnpm e2e` passes on replay with no network calls to the model.
- [ ] 4.2 Run the full backend suite, `ruff`, and the frontend unit tests, then regenerate the build walkthrough so the new spec tests appear. Verify everything passes and the walkthrough lists the new requirements.

## Workflow follow-up

- Archive the change, merge `records-year-fidelity` into `main`, and deploy after explicit approval. Then submit the clean sample on the hosted demo and confirm it ends approved without staff.
