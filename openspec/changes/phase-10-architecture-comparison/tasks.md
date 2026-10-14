# Tasks

## 1. Autonomous agent

- [ ] 1.1 Implement `app/autonomous.py` and `app/prompts/autonomous.py`: bound read-only tools, the loop with limits and the stuck guard, and the final decision. Verify with `tests/test_autonomous.py` against scripted turns: confirm after four calls with nothing written, a repeated call stopping as `needs_human`, and a vaccine check combining on-file and certificate records.

## 2. Comparison

- [ ] 2.1 Add `evals/comparison_cases.json` and the pure parts of `scripts/compare_architectures.py`: expected outcomes from true facts, outcome mapping, and scoring. Verify with `tests/test_compare_architectures.py`: confirmable truth, injection never confirmable, unsafe confirmation counted, hybrid outcome mapping, and the lab guard refusing non-local hosts.
- [ ] 2.2 Add the lab runner (database creation, migration, seeding, both architectures, report) and a scripted end-to-end test on two cases that also shows nothing is sent.
- [ ] 2.3 Show comparison reports side by side on the dashboard's Evals page. Verify with lint, the type check, the build, and a frontend test of the report shaping.

## 3. Real run and conclusion

- [ ] 3.1 Run the comparison for real over the whole set. Verify by committing the report and recording the numbers.
- [ ] 3.2 Write [decision record 0015](../../../docs/decisions/0015-hybrid-over-autonomous-measured.md) from the measured results. Verify it exists and that design D5 links to it.

## 4. Integration

- [ ] 4.1 Run both suites, lint, type check, build, `alembic check`, and the walkthrough coverage check. Regenerate the walkthrough. Verify all pass.
