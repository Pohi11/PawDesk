## ADDED Requirements

### Requirement: A pet already booked for the stay is not booked again
For boarding, the capacity check SHALL first look for a reservation of the same pet that shares a night with the stay. If one exists, no kennel SHALL be searched, capacity SHALL be reported as already booked, and the request SHALL move to `resolving` with the reason "capacity: <pet> already has a kennel for these nights". The resolver SHALL treat it as a problem that needs a person.

#### Scenario: Same pet, same nights
- **WHEN** Biscuit holds a kennel for Mar 24 to Mar 27 and a boarding request for Biscuit for Mar 24 to Mar 27 is checked, while medium kennels are free
- **THEN** capacity reports already booked with no kennel, the request moves to `resolving` with the reason "capacity: Biscuit already has a kennel for these nights", and the resolution is `not_attempted`

#### Scenario: Another pet's stay does not count
- **WHEN** Rosie holds a medium kennel for Mar 24 to Mar 27 and a boarding request for Biscuit for the same nights is checked, while another medium kennel is free
- **THEN** capacity reports a kennel found

### Requirement: Sending checks the pet again
Before reserving a kennel for a confirmed boarding request, sending SHALL check again that the pet has no reservation sharing a night with the stay. If it has one, the request SHALL move to `failed` without a reservation or a message.

#### Scenario: Pet booked before sending
- **WHEN** a clean boarding request for Biscuit is drafted, and Biscuit is reserved for the same nights before it is sent
- **THEN** the request is `failed` with the failed step `approved`, and no reservation or message is recorded for it
