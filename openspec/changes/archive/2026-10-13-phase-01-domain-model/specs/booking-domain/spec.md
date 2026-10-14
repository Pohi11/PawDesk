# Spec Delta

## Purpose

Defines the records a pet care facility needs before it can accept a booking (owners, pets, facilities, vaccine rules, vaccine records, kennels, and reservations) and the invariants that keep them consistent.

## ADDED Requirements

### Requirement: Pets belong to an owner and have a species
Every pet SHALL belong to exactly one owner and SHALL have a species of either `dog` or `cat`. A pet's weight SHALL be recorded in pounds and SHALL be greater than zero.

#### Scenario: Pet without an owner is rejected
- **WHEN** a pet is stored without an owner
- **THEN** the database rejects the record

#### Scenario: Unsupported species is rejected
- **WHEN** a pet is stored with species `rabbit`
- **THEN** the database rejects the record

#### Scenario: Non-positive weight is rejected
- **WHEN** a pet is stored with a weight of 0 lb
- **THEN** the database rejects the record

### Requirement: Size class is derived from species and weight
A pet's size class SHALL be derived, never entered by hand: every cat is `cat`. A dog is `small` under 20 lb, `medium` from 20 lb to under 50 lb, `large` from 50 lb to under 90 lb, and `xlarge` at 90 lb or more. The size class SHALL be recomputed whenever species or weight changes.

#### Scenario: Cat of any weight
- **WHEN** a cat weighing 14 lb is stored
- **THEN** its size class is `cat`

#### Scenario: Dog exactly on a boundary
- **WHEN** a dog weighing exactly 50 lb is stored
- **THEN** its size class is `large`

#### Scenario: Dog just under a boundary
- **WHEN** a dog weighing 19.9 lb is stored
- **THEN** its size class is `small`

#### Scenario: Weight change moves the class
- **WHEN** a 45 lb dog is updated to 52 lb
- **THEN** its size class changes from `medium` to `large`

### Requirement: Facilities have a time zone
Every facility SHALL have a name and an IANA time zone (for example `America/Chicago`), so that stay dates can later be interpreted in the facility's local time.

#### Scenario: Invalid time zone is rejected
- **WHEN** a facility is stored with time zone `Mars/Olympus`
- **THEN** the record is rejected before it reaches the database

### Requirement: Vaccine rules are defined per facility, service, and species
A facility SHALL define its required vaccines separately for each service (`boarding`, `daycare`, `grooming`) and species. The same vaccine SHALL NOT be required twice for the same facility, service, and species.

#### Scenario: Different rules per service
- **WHEN** a facility requires `bordetella` for dog daycare but not for dog grooming
- **THEN** looking up the dog grooming rules does not return `bordetella`

#### Scenario: Duplicate rule is rejected
- **WHEN** `rabies` is added twice to the same facility's dog boarding rules
- **THEN** the database rejects the second rule

### Requirement: Vaccine records store dates, not flags
A pet's vaccine record SHALL store the vaccine name, the date it was given, and its expiry date if one is known. An expiry date SHALL NOT be earlier than the date the vaccine was given.

#### Scenario: Record without expiry is allowed
- **WHEN** a vaccine record is stored with no expiry date
- **THEN** it is accepted, and the missing expiry is preserved as unknown rather than treated as valid

#### Scenario: Expiry before administration is rejected
- **WHEN** a vaccine record is stored with an expiry date earlier than the date given
- **THEN** the database rejects the record

### Requirement: Kennels have a size class
Every kennel SHALL belong to a facility and SHALL have one size class from the same set used for pets (`small`, `medium`, `large`, `xlarge`, `cat`).

#### Scenario: Kennel with unknown size class is rejected
- **WHEN** a kennel is stored with size class `huge`
- **THEN** the database rejects the record

### Requirement: Reservations never overlap on the same kennel
A reservation SHALL cover the nights from its start date up to, but not including, its end date. Its end date SHALL be after its start date. Two reservations for the same kennel SHALL NOT share any night, and the database itself SHALL enforce this.

#### Scenario: Overlapping reservation is rejected
- **WHEN** kennel K is reserved for Mar 6 to Mar 9 and another reservation for K is stored for Mar 8 to Mar 10
- **THEN** the database rejects the second reservation

#### Scenario: Back-to-back reservations are allowed
- **WHEN** kennel K is reserved for Mar 6 to Mar 9 and another reservation for K is stored for Mar 9 to Mar 12
- **THEN** both reservations are accepted, because the first checks out the morning the second checks in

#### Scenario: Same dates on different kennels are allowed
- **WHEN** kennels K1 and K2 are both reserved for Mar 6 to Mar 9
- **THEN** both reservations are accepted

#### Scenario: Zero-night reservation is rejected
- **WHEN** a reservation is stored with the same start and end date
- **THEN** the database rejects the record

### Requirement: A booking request creates at most one reservation
A reservation MAY reference the booking request that created it, and each booking request SHALL be referenced by at most one reservation, so that a retried step cannot double-book.

#### Scenario: Second reservation for the same request is rejected
- **WHEN** a reservation already exists for booking request R and another reservation for R is stored
- **THEN** the database rejects the second reservation
