# Tasks

## 1. Reply

- [x] 1.1 Add `promise_issues()`, `reply_facts()`, and the situation rules in `app/reply.py`, with the prompt in `app/prompts/reply.py`. Verify with `tests/test_reply.py` for: unconfirmed date, commitment without confirmation, price, clean reply, only verified options in the facts, `under_review` when nothing is offered.

## 2. Orchestration

- [x] 2.1 Add the `reply` step result and `outbound_messages` (migration), and the drafting, ready, approved, and rejected steps in the orchestrator. Update the existing orchestration tests. Verify with `tests/test_orchestrator.py` for: clean boarding request to `sent` with one reservation and one message, a resolved request waiting in `needs_review` with a resolution reason, a failed promise check waiting, a kennel taken before sending, a waiting request left alone, and the customer's message text never reaching the reply model.

## 3. Staff approval

- [ ] 3.1 Add `app/approvals.py` and the API routes. Verify with `tests/test_approvals_api.py` for: the queue, approve, edit and approve, reject with and without a reason, and acting twice.

## 4. Decision and real runs

- [ ] 4.1 Write [decision record 0011](../../../docs/decisions/0011-human-gate-before-sending.md). Verify it exists and that design D1 links to it.
- [ ] 4.2 Real runs: a clean request processed to `sent`, and a flagged request approved through the API to `sent`. Verify by recording the states, the drafted replies, the promise-check findings, and cost.

## 5. Integration

- [ ] 5.1 Run the full suite, lint, `alembic check`, and the spec-coverage check. Verify that all pass and every requirement in this change has a test with a matching `spec` marker.
