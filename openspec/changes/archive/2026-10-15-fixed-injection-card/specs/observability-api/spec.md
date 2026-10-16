# Spec Delta

## MODIFIED Requirements

### Requirement: Each sample is about a different pet
Every sample that names a pet SHALL name a different one, so the samples show different photos on the Try page. A sample whose card is not a benchmark image SHALL print its own pet's name and current records, so the planted instruction in the injection sample is the only reason it is held for staff. Every sample's card SHALL be a committed file served as stored, so the bytes sent to the model are the same on every platform.

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
