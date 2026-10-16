# Spec Delta

## MODIFIED Requirements

### Requirement: Each sample is about a different pet
Every sample that names a pet SHALL name a different one, so the samples show different photos on the Try page. Every sample's card SHALL be drawn in the one demo card style from its own pet's name, owner, and records, committed, and served as stored, so the bytes sent to the model are the same on every platform. No date given on a card SHALL be after the real date. The injection sample's records SHALL all be current, so the planted instruction is the only reason it is held.

#### Scenario: Distinct pets
- **WHEN** the samples are listed
- **THEN** no two samples that have a pet on file share the same pet id

#### Scenario: The injection sample's card matches its pet
- **WHEN** the injection sample's certificate image is requested
- **THEN** the API returns a PNG, and the same bytes on a second request

#### Scenario: The injection sample's card is a committed file
- **WHEN** the injection sample's certificate image is requested, on any platform
- **THEN** the API returns exactly the bytes of the committed card file

#### Scenario: The committed card shows Pepper's record
- **WHEN** Pepper's card is drawn again from her record
- **THEN** its pixels match the committed card file

#### Scenario: Every sample's card is a committed file
- **WHEN** the clean, injection, or expired vaccine sample's certificate image is requested, on any platform
- **THEN** the API returns exactly the bytes of that sample's committed card file

#### Scenario: Every committed card shows its pet's record
- **WHEN** each sample's card is drawn again from its pet's record
- **THEN** its pixels match the committed card file, and the record names that sample's pet and its owner on file

#### Scenario: No shot from the future
- **WHEN** each sample's card records are read
- **THEN** every vaccine's date given is on or before the real calendar date
