# Spec Delta

## ADDED Requirements

### Requirement: Previews carry their pet's photo fields
A generated request SHALL carry a pet id derived from its seed, and sending SHALL give the new pet that id. The demo samples list SHALL give each sample's pet id, species, and breed when the pet is on file, and none of them otherwise.

#### Scenario: The seed fixes the pet id
- **WHEN** seed 42 is previewed twice and then sent
- **THEN** both previews carry the same pet id, and the pet added on send has that id

#### Scenario: Sample pet fields
- **WHEN** the demo samples are listed
- **THEN** the clean boarding sample carries Biscuit's id, species, and breed, and the unknown-pet sample carries none
