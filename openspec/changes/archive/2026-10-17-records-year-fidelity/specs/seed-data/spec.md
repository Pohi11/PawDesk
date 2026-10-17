# Spec Delta

## ADDED Requirements

### Requirement: Seeded dates are anchored to the demo day
The seed command SHALL place every seeded date (vaccine records, reservations, booking requests) relative to the demo day that demo requests are processed against, not relative to the calendar day the seed runs. The seeded dataset SHALL therefore be the same whatever day the seed runs.

#### Scenario: Seeding on different days
- **WHEN** the seed command's arguments are read on two different calendar days
- **THEN** both runs use the demo day as the anchor date

#### Scenario: Records relative to the demo day
- **WHEN** the dataset is loaded with the demo day as the anchor
- **THEN** Biscuit's Bordetella on file was given 60 days before the demo day and expires 120 days after it
