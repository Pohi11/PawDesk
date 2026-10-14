# Tasks

## 1. Model client

- [x] 1.1 Add tool calling to `complete()`: a `tools` parameter, `ToolCall` and `assistant_message` on `LLMResult`, tool calls in the span output, and `require_parameters` when tools are offered. Verify with `tests/test_llm.py` tests for a scripted tool-call response and for the routing preference. Add an opt-in live test that the configured model calls a trivial tool.

## 2. Resolver

- [x] 2.1 Add `resolution_scope()` (eligibility) and the prompt builder in `app/resolver.py` and `app/prompts/resolver.py`. Verify with `tests/test_resolver.py` for: full nights eligible, unknown pet, suspected injection, `unknown_expiry` not attempted; and a test that the customer's message text never appears in the prompt.
- [x] 2.2 Implement the four tools with bound context and validated arguments. Verify with database tests: alternative dates three days later, an expired bordetella window, kennel sizes with medium full and large free, an invalid date range, a smaller kennel refused.
- [x] 2.3 Implement the loop with the stuck guard, the step limits, unknown-tool and invalid-argument handling, and verification of the proposal. Verify with scripted model turns: proposal after two calls, a repeated call stuck with no further model call, exactly 6 calls at the step limit, no proposal, `approve_booking` answered as unknown, verified and unverified options.

## 3. Orchestration

- [x] 3.1 Add the `resolution` step (migration for the step constraint) and the resolving step to the orchestrator: saved with the move to `drafting`, failures to `failed`, and retry. Update the existing orchestration tests for the new end state. Verify with `tests/test_orchestrator.py` for: resolution saved with the move, not attempted with no model call, model unavailable then retried.

## 4. Decision and real runs

- [x] 4.1 Write [decision record 0010](../../../docs/decisions/0010-bounded-proposal-only-resolver.md). Verify it exists and that design D1 links to it.
- [x] 4.2 Real runs from the command line: a Biscuit boarding request whose nights are full for every medium kennel (fill them with reservations in the dev database), and the existing Moose request left in `resolving` (expired bordetella). Verify by recording each outcome, the proposal and its verification, turns, tool calls, and cost.

## 5. Integration

- [ ] 5.1 Run the full suite, lint, `alembic check`, and the spec-coverage check. Verify that all pass and every requirement in this change has a test with a matching `spec` marker.

## Workflow follow-up

- Archive the change after review, which merges the specs into `openspec/specs/`.
- Merge `phase-07-resolver-agent` into `main`.
