# kennel-capacity Specification

## Purpose

Finds a kennel of a given size class that is free for every night of a stay, so that boarding requests can be answered from actual availability.

## Requirements

### Requirement: A kennel is free only if no night overlaps
A kennel SHALL be considered free for a stay when none of its reservations shares a night with the stay. A stay's nights run from the start date up to, but not including, the end date.

#### Scenario: Partly booked kennel is not free
- **WHEN** kennel M1 is reserved for Mar 6 to Mar 9 and a medium kennel is requested for Mar 8 to Mar 10, and M1 is the only medium kennel
- **THEN** no kennel is returned

#### Scenario: Back-to-back stay fits
- **WHEN** kennel M1 is reserved for Mar 6 to Mar 9 and a medium kennel is requested for Mar 9 to Mar 12
- **THEN** M1 is returned

### Requirement: Only the exact size class is searched
The search SHALL return only kennels of the requested size class at the requested facility.

#### Scenario: A free larger kennel is not offered
- **WHEN** all medium kennels are taken and a large kennel is free
- **THEN** a search for a medium kennel returns no kennel

#### Scenario: Other facilities are ignored
- **WHEN** another facility has a free medium kennel and this facility has none
- **THEN** a search at this facility returns no kennel

### Requirement: The choice among free kennels is deterministic
When several kennels qualify, the search SHALL return the one whose name sorts first, so the same request always gets the same kennel.

#### Scenario: Several free kennels
- **WHEN** medium kennels M2 and M3 are free and M1 is taken
- **THEN** M2 is returned

### Requirement: A stay has at least one night
A search SHALL be refused with an error when the end date is not after the start date.

#### Scenario: Zero-night search
- **WHEN** a kennel is requested from Mar 6 to Mar 6
- **THEN** the search fails with an error

### Requirement: Search reflects seeded availability
On the seeded dataset, the search SHALL reflect the seeded reservations.

#### Scenario: Seeded full medium weekend
- **WHEN** the seed has run today and a medium kennel is requested from 4 to 7 days from today
- **THEN** no kennel is returned

#### Scenario: Seeded free medium dates
- **WHEN** the seed has run today and a medium kennel is requested from 8 to 10 days from today
- **THEN** a kennel is returned
