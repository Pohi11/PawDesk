# pet-photos Specification

## Purpose
Gives every pet shown in the dashboard a recognizable photo that matches its species and breed, taken from a small committed set whose licensing and metadata are checked by tests.

## Requirements

### Requirement: A matched pet shows a photo of its breed
When a request's pet is matched and the photo set has a photo of that pet's species and breed, the dashboard SHALL show that photo. Breed matching SHALL ignore letter case and surrounding spaces. A pet SHALL never be shown with a photo of another species.

#### Scenario: Breed in the set
- **WHEN** the matched pet is a dog whose breed is "Beagle" and the set has a Beagle photo
- **THEN** the dashboard shows the Beagle photo

#### Scenario: Breed written differently
- **WHEN** the matched pet's breed is " beagle "
- **THEN** the dashboard shows the Beagle photo

#### Scenario: Same breed name, other species
- **WHEN** the matched pet is a cat whose breed matches only a dog photo's breed
- **THEN** the dashboard shows a cat photo

### Requirement: Other pets show a stable photo of their species
When the set has no photo of a matched pet's breed, or the pet has no breed, the dashboard SHALL show a photo of the pet's species chosen from the pet's id. The same pet SHALL get the same photo on every request and every page load.

#### Scenario: Breed not in the set
- **WHEN** the matched pet is a dog whose breed has no photo in the set
- **THEN** the dashboard shows one of the set's general dog photos

#### Scenario: Stable across requests
- **WHEN** two requests are matched to the same pet whose breed has no photo
- **THEN** both show the same photo

### Requirement: A request without a matched pet shows a placeholder
When a request has no matched pet, the dashboard SHALL show a placeholder that is visibly not a photo, with accessible text saying no pet is matched.

#### Scenario: Pet not on file
- **WHEN** a request's pet could not be matched to a pet on file
- **THEN** the dashboard shows the placeholder and no photo

### Requirement: Photos appear on the requests list and the run page
Each row of the requests list SHALL show the pet's photo or the placeholder beside the pet's name. The run page SHALL show it beside the pet's name in its heading. On a live run, the photo SHALL replace the placeholder once intake matches the pet, without reloading the page. Each photo SHALL have alternative text naming the pet.

#### Scenario: Requests list
- **WHEN** the requests list shows a request matched to Biscuit, a Beagle
- **THEN** its row shows the Beagle photo with alternative text naming Biscuit

#### Scenario: Live run
- **WHEN** a request is submitted from the demo and its run page is open before intake finishes
- **THEN** the page shows the placeholder first and the pet's photo after intake matches the pet, with no reload

### Requirement: Every committed photo is licensed for reuse and recorded
Every photo in the set SHALL be listed in a manifest with its species, breed (or none for a general photo), source page URL, author, and license. Every license SHALL be CC0 or a public-domain dedication. Every manifest entry SHALL have its file, and every file SHALL have a manifest entry.

#### Scenario: Manifest and files agree
- **WHEN** the photo folder and the manifest are compared
- **THEN** each file has exactly one entry and each entry's file exists

#### Scenario: Only reusable licenses
- **WHEN** the manifest is checked
- **THEN** every entry's license is CC0 or public domain and has a source URL on commons.wikimedia.org

#### Scenario: Every species has a general photo
- **WHEN** the manifest is checked
- **THEN** it has at least one general photo for each species the system supports

### Requirement: Committed photos carry no embedded metadata
Every committed photo SHALL be re-encoded so it carries no EXIF or XMP metadata, so no camera, location, or author data from the source file is republished.

#### Scenario: Metadata stripped
- **WHEN** each committed photo is read
- **THEN** it contains no EXIF or XMP block

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
