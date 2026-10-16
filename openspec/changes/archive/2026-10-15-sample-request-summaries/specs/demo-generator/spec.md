# Spec Delta

## ADDED Requirements

### Requirement: Samples carry a request summary
The demo samples list SHALL give each sample's service, start and end dates, owner name, and a plain-words summary of what its vaccine card shows. It SHALL give the pet's weight when the pet is on file, and none otherwise.

#### Scenario: A sample on file
- **WHEN** the demo samples are listed
- **THEN** the clean boarding sample carries boarding from 2027-03-24 to 2027-03-27, Biscuit's owner's name and weight, and says every vaccine on the card is current for the whole stay

#### Scenario: A sample not on file
- **WHEN** the demo samples are listed
- **THEN** the unknown-pet sample carries daycare on 2027-03-15 and its owner's name, no weight, and says no vaccine card is attached
