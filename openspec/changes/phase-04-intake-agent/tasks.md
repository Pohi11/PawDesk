# Tasks

## 1. Provider routing for structured requests

- [ ] 1.1 In `complete()`, add `provider.require_parameters: true` to the request body only when `response_format` is given. Verify with new tests in `tests/test_llm.py` that inspect the request body for both cases.

## 2. Intent schema

- [ ] 2.1 Add `BookingIntent` (Pydantic, `extra="forbid"`) and `strict_json_schema()` in `app/intake.py`. Verify with `tests/test_intake_schema.py`, covering valid parsing, an extra field rejected, out-of-range confidence rejected, and the strict schema with every field required, no additional properties, and no `title`/`default` keys.

## 3. Prompt and pipeline

- [ ] 3.1 Add the versioned prompt in `app/prompts/intake.py` (system rules, today's date and weekday, time zone, message delimited and neutralized). Verify with tests that the system message never contains the customer text and the user message wraps it in the delimiters.
- [ ] 3.2 Implement `run_intake()`: the oversize refusal, the model call with strict `response_format` and temperature 0, Pydantic validation, one repair carrying the errors, `IntakeInvalidOutput`, date and pet checks in code, confidence and ambiguity issues, the outcome, and the `intake` span with prompt version and output. Verify with `tests/test_intake.py` against scripted responses, covering every booking-intake scenario except the labeled set.

## 4. Labeled set and evaluation

- [ ] 4.1 Add `backend/evals/intake_cases.json` (16 cases, 3 injections) and `scripts/eval_intake.py` with a pure scoring function. Verify with `tests/test_intake_eval.py`, covering the set's shape and scoring per field and in total with scripted answers.
- [ ] 4.2 Run `uv run python -m scripts.eval_intake` against the real model. Verify that a report is written under `backend/evals/results/` and that the measured totals are recorded (not estimated).

## 5. Integration

- [ ] 5.1 Run the full suite, lint, and the spec-coverage check. Verify that all pass and every requirement in this change has a test with a matching `spec` marker.

## Workflow follow-up

- Archive the change after review, which merges the specs into `openspec/specs/`.
- Merge `phase-04-intake-agent` into `main`.
