# Spec Delta

## MODIFIED Requirements

### Requirement: Requirements link to their tests and latest results
For every current requirement, the output SHALL list the backend, frontend, and end-to-end tests that name it, each with its latest result (`passed`, `failed`, or `skipped`) and duration. It SHALL give the requirement an overall status:
- `verified` when it has at least one test and all of them passed;
- `failing` when any linked test failed;
- `untested` when it has no linked test.

#### Scenario: Verified requirement
- **WHEN** a requirement is named by one passing backend test and one passing frontend test
- **THEN** it lists both tests and is `verified`

#### Scenario: Failing requirement
- **WHEN** one of a requirement's linked tests failed in the latest report
- **THEN** the requirement is `failing`

#### Scenario: Untested requirement
- **WHEN** no test names a requirement
- **THEN** the requirement is `untested`

#### Scenario: End-to-end tests count
- **WHEN** a requirement is named only by a passing end-to-end test
- **THEN** it lists that test with the suite `e2e` and is `verified`
