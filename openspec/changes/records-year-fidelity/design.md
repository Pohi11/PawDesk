# Design

## Context

- **The records prompt** (`app/prompts/records.py`, `records-v1`) states today's date and lists the fields to return. It says dates are usually month/day/year, but nothing about keeping the printed year.
- **The failed hosted run** read Biscuit's card (Rabies 2024 to 2027, DHPP 2025 to 2028, Bordetella 2026 to 2027, Canine Influenza 2026 to 2028) as dates in 2024 and 2025, except Rabies, which it read correctly. The prompt told it today was 2027-03-03. So the dates were not pulled toward the stated today. They were pulled away from it, toward earlier years. The recorded end-to-end response for the same card (decision record [0016](../../../docs/decisions/0016-recorded-model-responses-for-ci.md)) has every date right.
- **Compliance uses every record**, on file and from the card. A vaccine is ok when any record covers the stay. So a misread card only changes the outcome when the records on file don't cover the stay either.
- **The seed** (`scripts/seed.py`) takes `today` as a parameter. `main()` passes `date.today()`. The hosted demo reseeds on every start (`deploy/huggingface/start.sh`). Demo requests are processed with `DEMO_TODAY` (`app/demo.py`, 2027-03-03), and the sample stays and cards use fixed 2027 dates.
- **Moose's seeded edge cases** are a large-kennel stay on days +7 to +14 and rabies expiring on day +10, partway through it. With the demo day as anchor, that stay is Mar 10 to 17, which overlaps the expired-vaccine sample's Mar 10 to 13. One pet can hold only one kennel per night, so the sample would be held for "Moose already has a kennel" instead of the vaccine.

## Goals / Non-Goals

**Goals:**
- Live reads of printed years are measurably more reliable, and the measurement is stored.
- Each sample's outcome follows from fixed data, whatever day the demo restarts.

**Non-Goals:**
- Catching a misread in code. Nothing in code knows what the card really says. See D3.
- Changing the committed cards. Their dates are what a real certificate would show, and the recordings are keyed by their bytes.
- Detecting duplicate requests. A boarding duplicate is already held by the one-kennel-per-pet check.

## Decisions

### D1. Tell the model to copy years as printed; keep stating today
- **New wording** after the date fields: copy every date exactly as printed, year included. Certificates often show dates after today, such as expiries one to three years ahead, and that is expected. Never change a date to bring it closer to today or to any other year.
- **`PROMPT_VERSION` becomes `records-v2`**, so spans and reports from before and after can be told apart (decision record [0007](../../../docs/decisions/0007-evaluating-llm-steps.md)).
- **The "Today is" line stays.** The misread moved dates away from the stated today, so that line isn't what caused it. It also tells the model that 2027 dates are present-day, not far future.
- **Alternative considered:** removing today from the prompt. The model would then fall back on its own sense of the current year, which is the likely source of the error.

### D2. Measure before and after with repeated reads of the sample cards
- **`scripts/eval_sample_cards.py`** reads each sample card (`biscuit.png`, `pepper.png`, `moose.png`) N times (default 20) through `run_records`, with `today=DEMO_TODAY` and the sample's pet as the booked pet. The model calls are real and the recorded-response transport is off.
- **The truth is the record each card was drawn from** (`scripts/draw_sample_cards.py`, `CARDS`), so the printed dates have one source.
- **Scoring is pure and unit-tested:**
  - A *misread* is any printed vaccine missing or any date differing.
  - A *decision flip* is a read whose card records alone give a different compliance outcome for the sample's stay than the printed records alone.
  - A *silent flip* is a flip the records step left `clear`.
  - The card is scored alone, because the records on file can hide a misread (Context).
- **Order matters:** the script lands and runs on `records-v1` before the prompt changes, then runs again on `records-v2`. Both reports are kept in `evals/results/` and are never edited.
- **The certificate benchmark v2 is run again on `records-v2`** and compared with the `records-v1` report from 2026-10-14, so the new wording is checked on 36 varied certificates and not only on three clean ones.
- **Alternative considered:** adding the sample cards to the benchmark as a v3. The benchmark scores one read per certificate, but this error shows up only in some reads, so it needs repeated reads of the same image.

### D3. No second read or code check in this change
- **A second read that must agree** (self-consistency) would catch a misread that varies between reads, at twice the model cost per certificate. Whether it's needed depends on the misread rate that `records-v2` leaves. If the after measurement still shows silent flips, it becomes its own change.
- **A plausibility check in code** has nothing to check against. A Bordetella given in 2024 and expiring in 2025 is a perfectly valid record. The records step's existing date checks (given after today, expiry before given) stay.

### D4. The seed command anchors to the demo day
- **`main()` passes `DEMO_TODAY`** instead of `date.today()`. `load()` and `seed()` keep their `today` parameter, so tests can still seed against any day.
- **Everything is then fixed in time:** records, reservations, and requests land on the same dates on every restart, and every sample stay sits in the same place relative to them.
- **Alternative considered:** processing demo requests against the real date and keeping the seed relative. The sample stays and cards are fixed 2027 dates baked into committed images and recordings. A moving today would eventually put every sample stay in the past.
- **Known gap, out of scope:** resuming a request after a staff decision (`app/api.py`) calls `process_request` without `today`, so it uses the facility's real date. The send step makes no date-sensitive check that this change affects.

### D5. Moose's edge cases move off the sample's nights
- **Moose's Bordetella on file matches his card:** given 474 days before the demo day (2025-11-14), expiring 109 days before it (2026-11-14). It no longer covers Mar 10 to 13, so the sample fails on Bordetella from either source.
- **Moose's seeded stay moves to days +21 to +28** (Mar 24 to 31), and his rabies on file expires on day +24 (Mar 27). This keeps the seed's "expires during an upcoming stay" edge case, and its nights don't touch the sample's.
- **Biscuit and Pepper are unchanged.** With the demo day as anchor, Biscuit's records on file cover Mar 24 to 27 by themselves, so the clean sample no longer depends on the card read. Pepper's on-file Bordetella stays expired and her card covers it, so only the planted instruction holds the injection sample.

### D6. A deterministic test for every sample's promise
- **A database test seeds with `DEMO_TODAY`,** then runs the compliance check and kennel search for each sample's stay, using its pet's records on file plus the records its card was drawn from. No model is involved.
- **It fails whenever a seed edit breaks a sample's story,** which is how the Moose overlap above would have been caught.

### D7. Recordings are made again
- **The prompt text is part of the recorded request,** so every records recording misses after D1. The end-to-end recordings are made again with `PAWDESK_E2E_RECORD=1 pnpm e2e` (decision record 0016), and the end-to-end suite then replays them.

## Risks / Trade-offs

- **[The new wording doesn't remove the misread]** → The after measurement shows it, and D3's second read becomes the next change. The demo's clean sample still passes, because of the records on file (D5).
- **[The clean sample's outcome hides a misread card]** → That's how a returning customer with current records on file behaves. The misread is still visible in the records step's evidence in the trace, and the measurement counts it.
- **[Small run counts]** → 20 reads per card can't show rare errors. The report gives the counts, not only rates, so nobody reads more into them than they support.
- **[Cost]** → About 60 reads per measurement, plus one benchmark run. The 36-certificate benchmark cost about two cents on 2026-10-14.

## Migration Plan

- Merge, then deploy. The Space restart reseeds with demo-day dates. There is no schema change. Requests already stored keep their traces.
- **Rollback:** revert the merge and redeploy. The restart reseeds with the old anchor.
