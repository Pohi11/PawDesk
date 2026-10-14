# Tasks

## 1. Generator

- [x] 1.1 Add `make_truth_v2()` (targets first, self-verifying against the compliance check) and a version argument to `scripts/generate_certificates.py`, leaving v1 generation byte-for-byte unchanged. Verify with `tests/test_certificates.py`, covering v2 determinism, the decision mix, boundary coverage, and a failed self-check raising.
- [ ] 1.2 Render v2 with `uv run python -m scripts.generate_certificates v2`. Verify that `tests/test_certificate_set.py` passes for both v1 (unchanged) and v2 (36 images with truth and a version field).

## 2. Evaluation

- [ ] 2.1 Add a version argument to `scripts/eval_records.py` (default `v2`) and a pure `build_report()` that records the benchmark version. Verify with `tests/test_records_eval.py` (report names `v2`; the default is v2).
- [ ] 2.2 Run `uv run python -m scripts.eval_records` against the real model on v2. Verify that the report is written and that the measured totals are recorded (not estimated).

## 3. Integration

- [ ] 3.1 Run the full suite, lint, and the spec-coverage check. Verify that all pass and both new requirements have matching `spec` markers.

## Workflow follow-up

- Archive the change, which merges the specs into `openspec/specs/`.
- Merge `certificate-benchmark-v2` into `main`.
