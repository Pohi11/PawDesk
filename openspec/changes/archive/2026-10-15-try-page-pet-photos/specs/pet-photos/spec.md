# Spec Delta

## ADDED Requirements

### Requirement: The Try page shows each request's pet photo
Each sample in the Try page's list SHALL show its pet's photo, or the placeholder when the sample's pet is not on file. A generated request SHALL show its pet's photo on the "Make one up" choice and beside the preview's heading, chosen by the same rules as everywhere else, so it is the photo the run page shows once the request is sent.

#### Scenario: A sample's pet
- **WHEN** the Try page lists the clean boarding sample, whose pet is Biscuit, a Beagle
- **THEN** the sample shows the Beagle photo with alternative text naming Biscuit

#### Scenario: A sample without a pet on file
- **WHEN** the Try page lists the unknown-pet sample
- **THEN** the sample shows the placeholder

#### Scenario: A generated pet keeps its photo
- **WHEN** a generated pet whose breed has no photo in the set is previewed and then sent
- **THEN** the preview and the run page show the same general photo
