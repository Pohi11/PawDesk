## ADDED Requirements

### Requirement: Running a boarding sample frees its stay
Before a fixed boarding sample's request is stored, the API SHALL release every reservation made by an earlier request that is in a kennel of the sample pet's size class and shares a night with the sample's stay. Reservations without a request, such as seeded ones, SHALL be kept. Samples for other services SHALL release nothing.

#### Scenario: Earlier runs filled the kennels
- **WHEN** earlier requests hold every medium kennel for Mar 24 to Mar 27 and the clean boarding sample is submitted
- **THEN** those reservations are released before the request is stored, and a medium kennel is free for its stay

#### Scenario: Seeded reservations stay
- **WHEN** a seeded reservation without a request holds a medium kennel for nights in the clean sample's stay and the sample is submitted
- **THEN** the seeded reservation is kept

#### Scenario: Other stays stay
- **WHEN** an earlier request holds a medium kennel for Mar 28 to Mar 30, or a large kennel for Mar 24 to Mar 27, and the clean boarding sample is submitted
- **THEN** both reservations are kept
