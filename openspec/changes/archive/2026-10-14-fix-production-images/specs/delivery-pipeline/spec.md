# Spec Delta

## MODIFIED Requirements

### Requirement: Every change is checked automatically
The pipeline SHALL run on every push and pull request, with no secret except the scanner's own token, and SHALL run:
- the backend lint, migrations, migration check, and tests against a Postgres service;
- the frontend lint, type check, unit tests, and build;
- the end-to-end tests with recorded responses;
- the spec-coverage check over all three test reports;
- a secret scan of the repository history;
- a build of both production images, and an import of the app inside the backend image, which holds runtime dependencies only.

#### Scenario: Pipeline definition
- **WHEN** the pipeline definition is read
- **THEN** it triggers on push and pull request and contains a job for each check above, and no step uses a model API key

#### Scenario: Undeclared runtime dependency
- **WHEN** the app imports a third-party package that is not a declared runtime dependency
- **THEN** a test fails and names the package
