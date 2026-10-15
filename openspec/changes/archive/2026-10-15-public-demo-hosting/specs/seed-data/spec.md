# Spec Delta

## MODIFIED Requirements

### Requirement: Seeding refuses non-development databases
The seed command SHALL refuse to run unless the target database is a local development or test database, or its host is exactly the one named in `PAWDESK_SEED_ALLOWED_HOST`, because it deletes existing data.

#### Scenario: Remote database is refused
- **WHEN** the seed command is pointed at a database whose host is not `localhost`, `127.0.0.1`, or `postgres`, and no allowed host is named
- **THEN** it exits with an error and changes nothing

#### Scenario: A different remote host is still refused
- **WHEN** an allowed host is named and the database's host is a different remote host
- **THEN** it exits with an error and changes nothing

#### Scenario: The named remote host is seeded
- **WHEN** an allowed host is named and the database's host is exactly that host
- **THEN** the host check passes
