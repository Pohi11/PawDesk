# Spec Delta

## ADDED Requirements

### Requirement: Instants convert to the facility's calendar date
Converting a moment in time to a date SHALL use the facility's time zone. A moment without a time zone SHALL be rejected rather than guessed.

#### Scenario: Late evening in Chicago is already tomorrow in UTC
- **WHEN** the instant 2027-03-07 03:30 UTC is converted for a facility in `America/Chicago`
- **THEN** the date is 2027-03-06

#### Scenario: Ahead-of-UTC facility
- **WHEN** the instant 2027-03-06 20:00 UTC is converted for a facility in `Asia/Tokyo`
- **THEN** the date is 2027-03-07

#### Scenario: Naive time is rejected
- **WHEN** a datetime with no time zone is converted
- **THEN** the conversion fails with an error
