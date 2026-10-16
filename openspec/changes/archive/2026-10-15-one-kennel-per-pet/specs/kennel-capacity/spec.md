## ADDED Requirements

### Requirement: A pet holds at most one kennel per night
Two reservations for the same pet SHALL NOT share a night. The database SHALL refuse such a reservation, whichever kennels the two are in. A pet's reservations that share a night with a stay SHALL be found by pet and dates alone.

#### Scenario: Second kennel for the same nights refused
- **WHEN** Biscuit is reserved in M1 for Mar 24 to Mar 27 and a reservation for Biscuit in M2 for Mar 26 to Mar 28 is inserted
- **THEN** the database refuses it

#### Scenario: Back-to-back stays for one pet
- **WHEN** Biscuit is reserved in M1 for Mar 24 to Mar 27 and a reservation for Biscuit in M2 for Mar 27 to Mar 29 is inserted
- **THEN** it is stored

#### Scenario: Finding a pet's overlapping stay
- **WHEN** Biscuit is reserved for Mar 24 to Mar 27 and Biscuit's reservations for Mar 26 to Mar 30 are looked up
- **THEN** the Mar 24 to Mar 27 reservation is found, and a lookup for Mar 27 to Mar 30 finds none
