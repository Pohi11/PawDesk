# Spec Delta

## ADDED Requirements

### Requirement: Seeding can leave out booking requests
The seed command SHALL accept `--no-requests`. With it, the seed SHALL load the same facility, vaccine rules, kennels, owners, pets, vaccine records, and reservations as without it, and no booking requests, transitions, or approvals. Without it, the seed SHALL load the full dataset.

#### Scenario: Seed without requests
- **WHEN** the seed runs with booking requests left out
- **THEN** there are no booking requests, transitions, or approvals, and every other table has the same row count as after a full seed

#### Scenario: Full seed by default
- **WHEN** the seed command's arguments are read without `--no-requests`
- **THEN** booking requests are included, and with `--no-requests` they are left out
