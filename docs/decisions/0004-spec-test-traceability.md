# 0004 — Link every test to the spec requirement it verifies

- **Date:** 2026-10-13
- **Status:** Accepted

## Context

Requirements live in `openspec/specs/` as `### Requirement:` blocks with WHEN/THEN scenarios (decision record 0001). The build walkthrough page has to show, for any requirement, which tests verify it and whether they passed in the latest run. That needs a machine-readable link from each test to its requirement. The link has to exist from the very first spec, because adding it to hundreds of existing tests later is slow and error-prone.

## Options considered

1. **Naming convention** (for example, `test_booking_lifecycle__only_listed_transitions`). Needs no tooling, but requirement names contain spaces and punctuation. Renames silently break the link, and one test can't cover two requirements.
2. **Docstring tags** (for example, `Spec: booking-lifecycle / …`). Easy to read, but it's free text that needs custom parsing, and nothing validates it.
3. **A registered pytest marker**, `@pytest.mark.spec("<capability>", "<requirement name>")`. It's structured and validated by pytest (`--strict-markers` rejects typos in the marker name). A test can carry several markers, and the marker can be exported through pytest's standard JUnit XML.
4. **A separate mapping file** (YAML from requirement to test IDs). Keeps tests untouched, but drifts from the code it describes.

## Decision

Option 3.

- Every test that verifies a requirement carries `@pytest.mark.spec(capability, requirement)`, where `capability` is the spec folder name and `requirement` is the exact `### Requirement:` title.
- A hook in `tests/conftest.py` rejects malformed markers. It also copies each marker into the test's JUnit XML properties as `<property name="spec" value="<capability>: <requirement>"/>`.
- Tests of infrastructure with no spec behavior (for example, test-database isolation) carry no marker.
- The convention is tested itself, in `tests/test_spec_traceability.py`.

## Consequences

- **Good:** A standard JUnit XML report holds everything needed to join tests and results to requirements. No custom test runner is required.
- **Good:** A test can verify several requirements by stacking markers.
- **Cost:** Requirement titles become identifiers. Renaming a requirement means updating its markers. A coverage check (every requirement has at least one marked test, and every marker names an existing requirement) catches drift. It runs at the end of each change and becomes automatic with the build walkthrough page.
- **Cost:** The link is only as accurate as the marker. A test can be marked with a requirement it doesn't really verify. Review is the guard against that.
