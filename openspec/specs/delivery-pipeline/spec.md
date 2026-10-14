# delivery-pipeline Specification

## Purpose
Checks every change automatically: backend and frontend checks, the end-to-end demo against recorded model responses, spec coverage, and a secret scan, so a change that breaks any of them is caught before it is merged.

## Requirements

### Requirement: The demo runs end to end against recorded responses
End-to-end tests SHALL run the real backend and dashboard against a freshly migrated and seeded database, with the model client replaying recorded responses. They SHALL drive the dashboard in a browser through the demo's main paths.

#### Scenario: Clean sample to sent
- **WHEN** the clean demo sample is submitted from the demo page
- **THEN** the live run view shows the request reaching `sent`

#### Scenario: Injection to review to sent
- **WHEN** the injection sample is submitted, and a staff member approves it from the review queue
- **THEN** the request first waits in review with its flag reasons, and then reaches `sent`

### Requirement: Every change is checked automatically
The pipeline SHALL run on every push and pull request, with no secret except the scanner's own token, and SHALL run:
- the backend lint, migrations, migration check, and tests against a Postgres service;
- the frontend lint, type check, unit tests, and build;
- the end-to-end tests with recorded responses;
- the spec-coverage check over all three test reports;
- a secret scan of the repository history.

#### Scenario: Pipeline definition
- **WHEN** the pipeline definition is read
- **THEN** it triggers on push and pull request and contains a job for each check above, and no step uses a model API key

### Requirement: Secrets never enter the repository
No tracked file SHALL contain a value shaped like a real model provider key, and the example environment file SHALL contain only placeholders.

#### Scenario: Key-shaped value in a tracked file
- **WHEN** a tracked file contains a string shaped like a real OpenRouter key
- **THEN** the secret check fails and names the file

#### Scenario: Clean repository
- **WHEN** the repository's tracked files are scanned
- **THEN** no key-shaped value is found
