# seed-data Specification

## Purpose

Provides a repeatable, fully synthetic dataset that covers the situations later phases must handle, so development, demos, and manual testing start from a known state.

## Requirements

### Requirement: Seeding loads a known synthetic dataset
A single seed command SHALL load at least one facility with vaccine rules for every service and species, kennels of every size class, owners, dogs and cats across size classes, vaccine records, existing reservations, and booking requests in several lifecycle states. All names, contacts, and records SHALL be fictional.

#### Scenario: Seed populates every table
- **WHEN** the seed command runs against an empty, migrated database
- **THEN** every domain table has at least one row and kennels exist for all five size classes

#### Scenario: Seed covers vaccine edge cases
- **WHEN** the seed command has run
- **THEN** the dataset includes at least one pet with an expired vaccine, one with a vaccine that expires during an upcoming stay, and one with a vaccine record that has no expiry date

### Requirement: Seeding is repeatable
Running the seed command again SHALL replace the seeded data with the same dataset rather than adding duplicates or failing.

#### Scenario: Running seed twice
- **WHEN** the seed command runs twice in a row
- **THEN** the row counts after the second run equal those after the first

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

### Requirement: Seeding can leave out booking requests
The seed command SHALL accept `--no-requests`. With it, the seed SHALL load the same facility, vaccine rules, kennels, owners, pets, vaccine records, and reservations as without it, and no booking requests, transitions, or approvals. Without it, the seed SHALL load the full dataset.

#### Scenario: Seed without requests
- **WHEN** the seed runs with booking requests left out
- **THEN** there are no booking requests, transitions, or approvals, and every other table has the same row count as after a full seed

#### Scenario: Full seed by default
- **WHEN** the seed command's arguments are read without `--no-requests`
- **THEN** booking requests are included, and with `--no-requests` they are left out

### Requirement: Seeded dates are anchored to the demo day
The seed command SHALL place every seeded date (vaccine records, reservations, booking requests) relative to the demo day that demo requests are processed against, not relative to the calendar day the seed runs. The seeded dataset SHALL therefore be the same whatever day the seed runs.

#### Scenario: Seeding on different days
- **WHEN** the seed command's arguments are read on two different calendar days
- **THEN** both runs use the demo day as the anchor date

#### Scenario: Records relative to the demo day
- **WHEN** the dataset is loaded with the demo day as the anchor
- **THEN** Biscuit's Bordetella on file was given 60 days before the demo day and expires 120 days after it
