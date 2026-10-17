# Proposal

## Why

On the hosted demo, the clean boarding sample was held for staff with "vaccine bordetella: expired", even though its card prints Bordetella valid through Nov 3, 2027. The records step read the card's years wrong: every date printed after 2024 except Rabies's expiry came back one to three years earlier, in 2024 or 2025 (Bordetella read as given 2024-10-12 and expiring 2025-11-03). It still reported confidence 0.95 and no ambiguities, so nothing in the records step flagged the error. The recorded test run of the same card read every date correctly, so the error shows up in some live reads but not others.

Two things let that one misread change the outcome:

- **The model is not told to keep printed years as they are.** The prompt states today's date, and the misread dates all fall closer to the model's own sense of "now". The prompt never says that dates later than today are normal and must be copied unchanged.
- **The seeded records on file drift with the day the seed runs.** The seed places every date relative to the real calendar day, while demo requests are processed as if today were the demo day (Mar 3, 2027). Seeded on Oct 16, 2026, Biscuit's Bordetella on file expires Feb 13, 2027, before the sample stay. If it were anchored to the demo day, it would cover the stay. The same drift breaks the expired-vaccine sample once the demo is reseeded on or after Nov 3, 2026: Moose's Bordetella on file would then cover his Mar 10 to 13 stay, and the sample would pass.

## What Changes

- **The records prompt tells the model to copy every date exactly as printed,** including the year, and says that dates after today are expected and must not be adjusted. The prompt version becomes `records-v2`.
- **The seed command anchors every date to the demo day** instead of the real calendar day, so the hosted demo's data is the same whenever it restarts.
- **Moose's seeded edge cases move off the expired-vaccine sample's nights.** Moose's Bordetella on file is expired before Mar 10, and his seeded upcoming stay (where rabies runs out partway through) moves to nights that don't overlap Mar 10 to 13. The edge cases themselves are kept.
- **A deterministic test checks that each sample ends as it promises.** From the seeded records and the dates printed on each sample's card, with no model involved, the clean sample is compliant with a free kennel, the injection sample is compliant, and the expired-vaccine sample fails only on Bordetella.
- **A new evaluation reads each sample card many times with the live model** and reports how often any printed date is misread and how often a misread changes the sample's compliance outcome. It runs once on `records-v1` before the prompt change and once on `records-v2` after. The certificate benchmark v2 is also run again on `records-v2` to check that the new wording doesn't lower its accuracy.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `vaccine-records-extraction`: the prompt tells the model to copy printed dates, years included, exactly.
- `seed-data`: seeded dates are anchored to the demo day, not the day the seed runs.
- `observability-api`: each sample's promised outcome follows from the seeded records and its printed card alone.
- `certificate-evaluation`: an evaluation that reads the sample cards repeatedly and reports the misread rate and the decision flips.

## Impact

- **Backend:** `app/prompts/records.py` (wording, `PROMPT_VERSION`), `scripts/seed.py` (anchor day, Moose's records and stay), a new `scripts/eval_sample_cards.py`.
- **Tests:** a records prompt test, seed anchor test, a sample outcome test, scoring tests for the new evaluation, and the tests that read Moose's seeded stay (`tests/test_compliance_db.py`).
- **Recorded model responses:** the end-to-end recordings are keyed by the request, so the prompt change makes them miss. They are recorded again.
- **Results:** two sample-card reports and one benchmark v2 report are added to `evals/results/`. These are live model calls and cost a small amount.
- **Hosted demo:** after deploy, the restart reseeds with demo-day dates. No migration.
