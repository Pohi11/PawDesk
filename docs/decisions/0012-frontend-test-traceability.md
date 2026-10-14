# 0012 — Frontend tests carry their spec link in the test name

- **Date:** 2026-10-14
- **Status:** Accepted
- **Extends:** [0004](0004-spec-test-traceability.md)

## Context

Decision record 0004 links every backend test to the requirement it verifies, through a pytest marker exported into JUnit XML. The dashboard adds frontend requirements, such as how the run graph derives step status, how the timeline lays out overlapping spans, and which paths the proxy forwards. Their tests run under Vitest, not pytest. The coverage check and the build walkthrough page need the same link from these tests.

## Options considered

1. **Vitest test annotations or metadata.** Structured, but whether and how they reach the JUnit report differs between versions, so the link would depend on reporter internals.
2. **A mapping file** from requirement to test names. Rejected in 0004 for the same reason: it drifts from the code.
3. **A tag in the test name,** `[spec <capability>: <requirement>] <description>`, written by a small `specTest()` helper that refuses malformed tags. Vitest's built-in JUnit reporter writes test names unchanged.

## Decision

Option 3.
- **Writing tags:** `frontend/tests/spec.ts` provides `specTest(capability, requirement, name, fn)` and the tag pattern. The pattern is tested.
- **Reporting:** `pnpm test` writes `frontend/test-results/junit.xml`.
- **Checking:** the coverage check reads both JUnit reports. A requirement is covered when a backend `spec` property or a frontend tag names it, and the covering tests passed.

## Consequences

- **Good:** One requirement can be covered by backend and frontend tests together, and the walkthrough page shows both.
- **Good:** No dependency on reporter metadata features; any JUnit reader sees the tag.
- **Cost:** Requirement titles appear in test names, so renaming a requirement means updating both test languages. The coverage check catches drift, as in 0004.
