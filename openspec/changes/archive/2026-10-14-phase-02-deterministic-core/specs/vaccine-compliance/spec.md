# Spec Delta

## Purpose

Decides whether a pet's vaccine records satisfy a facility's vaccine rules for a service over a stay. It explains the result for each required vaccine and separates definite failures from cases that need a person to look.

## ADDED Requirements

### Requirement: A vaccine must cover every day the pet is on site
A pet is on site every date from the stay's start date through its end date, inclusive. For a day service the start and end are the same date. A vaccine record SHALL cover the stay only if it was given on or before the start date and its expiry date is on or after the end date. The expiry date is the last day the vaccine is valid.

#### Scenario: Expires on checkout day
- **WHEN** a stay runs Mar 6 to Mar 9 and the rabies record was given Jan 1 and expires Mar 9
- **THEN** rabies is `ok`

#### Scenario: Expires the day before checkout
- **WHEN** a stay runs Mar 6 to Mar 9 and the rabies record expires Mar 8
- **THEN** rabies is `expires_during_stay`

#### Scenario: Expires on check-in day
- **WHEN** a stay runs Mar 6 to Mar 9 and the rabies record expires Mar 6
- **THEN** rabies is `expires_during_stay`

#### Scenario: Expired before check-in
- **WHEN** a stay runs Mar 6 to Mar 9 and the only rabies record expires Mar 5
- **THEN** rabies is `expired`

#### Scenario: Given after check-in
- **WHEN** a stay runs Mar 6 to Mar 9 and the only rabies record was given Mar 7
- **THEN** rabies is `not_yet_given`

#### Scenario: Day service on the expiry date
- **WHEN** a daycare visit is on Mar 6 and the bordetella record expires Mar 6
- **THEN** bordetella is `ok`

### Requirement: Any covering record satisfies the vaccine
When a pet has several records for the same vaccine, the vaccine SHALL be `ok` if any one record covers the stay, whatever the other records say.

#### Scenario: Booster replaces an expired shot
- **WHEN** one rabies record expired last year and another expires next year
- **THEN** rabies is `ok` for a stay next month

#### Scenario: Known expiry outweighs an unknown one
- **WHEN** one rabies record has no expiry date and another covers the stay
- **THEN** rabies is `ok`

### Requirement: Uncovered vaccines get the most useful explanation
When no record covers the stay, the vaccine's status SHALL be the first that applies: `missing` (no records at all), `unknown_expiry` (a record given on or before the start date has no expiry date), `expires_during_stay` (a record given on or before the start date expires on or after the start date but before the end date), `not_yet_given` (a record was given after the start date), `expired` (every record expired before the start date).

#### Scenario: No records at all
- **WHEN** the pet has no bordetella records and bordetella is required
- **THEN** bordetella is `missing`

#### Scenario: Unknown expiry with nothing better
- **WHEN** the only FVRCP record was given before the stay and has no expiry date
- **THEN** FVRCP is `unknown_expiry`

#### Scenario: Mid-stay expiry beats an older expired record
- **WHEN** one rabies record expired last year and another expires during the stay
- **THEN** rabies is `expires_during_stay`

### Requirement: Outcome separates failures from human review
The overall outcome SHALL be `not_compliant` if any required vaccine is `missing`, `expired`, `expires_during_stay`, or `not_yet_given`. Otherwise it SHALL be `needs_review` if any is `unknown_expiry`. Otherwise it SHALL be `compliant`. A service with no required vaccines SHALL be `compliant`.

#### Scenario: Everything covered
- **WHEN** every required vaccine is `ok`
- **THEN** the outcome is `compliant`

#### Scenario: Unknown expiry alone
- **WHEN** every required vaccine is `ok` except one that is `unknown_expiry`
- **THEN** the outcome is `needs_review`

#### Scenario: A definite failure outweighs unknown expiry
- **WHEN** one required vaccine is `unknown_expiry` and another is `missing`
- **THEN** the outcome is `not_compliant`

#### Scenario: No rules for the service
- **WHEN** the facility requires no vaccines for the service and species
- **THEN** the outcome is `compliant`

### Requirement: Only required vaccines are judged
The result SHALL contain exactly one entry per required vaccine. Records for vaccines that aren't required SHALL NOT affect the result.

#### Scenario: Extra records are ignored
- **WHEN** only rabies is required and the pet also has an expired leptospirosis record
- **THEN** the result contains only rabies, and the outcome depends only on rabies

### Requirement: Invalid stays are rejected
A check SHALL be refused with an error when the end date is before the start date.

#### Scenario: End before start
- **WHEN** a check is requested for a stay from Mar 9 to Mar 6
- **THEN** it fails with an error and returns no result

### Requirement: Rules and records come from the facility and the pet
For a stored pet, the check SHALL use the facility's vaccine rules for the requested service and the pet's species, and every vaccine record stored for that pet.

#### Scenario: Seeded pet with an expired vaccine
- **WHEN** the seeded dog Pepper is checked for boarding over a stay starting next week
- **THEN** bordetella is `expired` and the outcome is `not_compliant`

#### Scenario: Seeded pet with unknown expiry
- **WHEN** the seeded cat Olive is checked for boarding over a stay starting next week
- **THEN** FVRCP is `unknown_expiry` and the outcome is `needs_review`
