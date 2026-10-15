## ADDED Requirements

### Requirement: Each sample is about a different pet
Every sample that names a pet SHALL name a different one, so the samples show different photos on the Try page. A sample whose card is not a benchmark image SHALL print its own pet's name and current records, so the planted instruction in the injection sample is the only reason it is held for staff.

#### Scenario: Distinct pets
- **WHEN** the samples are listed
- **THEN** no two samples that have a pet on file share the same pet id

#### Scenario: The injection sample's card matches its pet
- **WHEN** the injection sample's certificate image is requested
- **THEN** the API returns a PNG, and the same bytes on a second request
