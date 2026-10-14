# Tasks

## 1. Date semantics

- [x] 1.1 Write [decision record 0005](../../../docs/decisions/0005-stay-date-semantics.md) (stay date semantics). Verify the file exists and that design D1 links to it.
- [x] 1.2 Add `facility_date()` in `app/dates.py`. Verify with `tests/test_dates.py`, covering the Chicago, Tokyo, and naive-datetime scenarios.

## 2. Vaccine compliance (pure)

- [x] 2.1 Write `tests/test_compliance.py`: the boundary table (expiry Mar 5/6/8/9/10 for a Mar 6–9 stay; given Mar 7), day service on the expiry date, booster and unknown-expiry combinations, the precedence order, every outcome rule, extra records ignored, and end-before-start rejected. Verify that it collects and fails against a stub.
- [x] 2.2 Implement `app/compliance.py` (value types, `check()`). Verify that `tests/test_compliance.py` passes in full.

## 3. Compliance loader

- [x] 3.1 Add `load_requirements()`, `load_evidence()`, and `check_pet()`. Verify with `tests/test_compliance_db.py`, covering the seeded Pepper (`expired`, `not_compliant`) and Olive (`unknown_expiry`, `needs_review`) scenarios against the seeded test database.

## 4. Kennel capacity

- [x] 4.1 Write `tests/test_capacity.py`: partly booked, back-to-back, exact size only, other facility ignored, deterministic choice, zero-night rejected, and the seeded full and free medium windows. Verify that it collects and fails against a stub.
- [x] 4.2 Implement `app/capacity.py` (`find_kennel()`, a single `NOT EXISTS` query). Verify that `tests/test_capacity.py` passes in full.

## 5. Integration

- [ ] 5.1 Run the full suite, lint, and the spec-coverage check. Verify that `uv run pytest` and ruff pass, and that every requirement in this change has at least one test with a matching `spec` marker.

## Workflow follow-up

- Archive the change after review, which merges the specs into `openspec/specs/`.
- Merge `phase-02-deterministic-core` into `main`.
