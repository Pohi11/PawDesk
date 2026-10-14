# Tasks

## 1. Shared structured extraction

- [x] 1.1 Add `app/structured.py` (`extract()`, `InvalidModelOutput`, strict schema and response format moved from intake). Switch `app/intake.py` to it, with `IntakeInvalidOutput` subclassing `InvalidModelOutput`. Verify that every existing intake test passes unchanged, and add `tests/test_structured.py` for the helper.

## 2. Records step

- [x] 2.1 Add `CertificateExtraction` / `ExtractedRecord` and the versioned prompt (`app/prompts/records.py`). Verify with schema tests (extra fields rejected, confidence range, strict schema) and prompt tests (no-inference rule, vocabulary, image part present).
- [ ] 2.2 Implement `run_records()` in `app/records.py`: image type and size checks by magic bytes, the model call through the shared helper, code checks (dates, unmapped labels, pet name, no records), doubt issues, the outcome, conversion to `VaccineEvidence`, and the `records` span with prompt version and image hash. Verify with `tests/test_records.py` against scripted answers, covering every vaccine-records-extraction scenario.

## 3. Synthetic certificates

- [ ] 3.1 Add `playwright` and `pillow` as dev dependencies, install Chromium, vendor OFL fonts with their licenses, and implement the pure ground-truth generator. Verify with `tests/test_certificates.py`, covering deterministic truth, variant coverage, synthetic marking in the rendered HTML, and fictional names.
- [ ] 3.2 Render the 36-certificate set with `uv run python -m scripts.generate_certificates`. Verify that 36 PNGs and `truth.json` exist, and that the loaded-set test (each image has truth, at least 30) passes.

## 4. Evaluation

- [ ] 4.1 Implement `scripts/eval_records.py` with pure matching, scoring, invented-expiry, and decision-agreement functions. Verify with `tests/test_records_eval.py` against the spec's scoring scenarios, plus a scripted end-to-end run on two certificates.
- [ ] 4.2 Write [decision record 0007](../../../docs/decisions/0007-evaluating-llm-steps.md) (how LLM steps are evaluated). Verify the file exists and that design D7 links to it.
- [ ] 4.3 Run `uv run python -m scripts.eval_records` against the real model. Verify that a report is written under `backend/evals/results/` and that the measured totals are recorded (not estimated).

## 5. Integration

- [ ] 5.1 Run the full suite, lint, and the spec-coverage check. Verify that all pass and every requirement in this change has a test with a matching `spec` marker.

## Workflow follow-up

- Archive the change after review, which merges the specs into `openspec/specs/`.
- Merge `phase-05-records-agent` into `main`.
