# build-walkthrough Specification

## Purpose
Shows how PawDesk was built, generated from the repository's public sources: the archived changes, the requirements they produced with the tests that verify them and their latest results, and the decisions they relied on. The page describes the method, never who did what.

## Requirements

### Requirement: The walkthrough is generated from public sources only
The generator SHALL read only the archived OpenSpec changes, the current specs, the decision records, and the JUnit test reports. It SHALL NOT read the working agreement, the build plan, or anything under `docs/private/`. Its output SHALL record when it was generated and when each test report was produced.

#### Scenario: Every archived change appears
- **WHEN** the repository holds three archived changes
- **THEN** the output lists all three, in date order, each with its date, motivation, tasks with their completion, and the requirements its spec deltas added or modified

#### Scenario: Private files are never read
- **WHEN** a private notes file contains a marker string
- **THEN** the marker appears nowhere in the output

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

### Requirement: Changes link to the decisions they relied on
Each change in the output SHALL list the decision records its proposal, design, or tasks link to. Every decision record SHALL appear in the output with its number, title, date, status, and full text.

#### Scenario: Decision linked from a change
- **WHEN** a change's design links to decision record 0008
- **THEN** that change lists 0008, and 0008 appears among the decisions

### Requirement: The coverage check fails on gaps
In check mode, the generator SHALL exit with an error when any requirement is not `verified`, or when a test names a requirement that doesn't exist, and SHALL print each problem.

#### Scenario: Gap found
- **WHEN** a requirement is untested, or a test names an unknown requirement
- **THEN** check mode exits with an error naming it

#### Scenario: Complete coverage
- **WHEN** every requirement is verified and every test names an existing requirement
- **THEN** check mode exits successfully

### Requirement: Readers can follow every link in the pages
The walkthrough pages SHALL:
- give every requirement and decision a stable anchor;
- link each change's requirements to their entries in the spec browser;
- link each change's decisions to their entries on the decisions page.

#### Scenario: From a change to a requirement's tests
- **WHEN** a reader follows a requirement from a change on the timeline
- **THEN** they reach that requirement in the spec browser, where its tests and latest results are listed

#### Scenario: Stable anchors
- **WHEN** an anchor is built for the same requirement twice
- **THEN** it is identical both times, and different requirements get different anchors
