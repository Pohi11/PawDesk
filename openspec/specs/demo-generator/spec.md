# demo-generator Specification

## Purpose
Makes up demo booking requests on the spot, each with a vaccine certificate that matches it, so the desk can be shown handling requests it was never tuned on, and the certificate can be read by a person before the model reads it.

## Requirements

### Requirement: Random requests are reproducible
Given a seed, the generator SHALL produce a request from a seeded owner for a new pet. The request SHALL include:
- a service the facility has vaccine rules for, for that species;
- a stay starting 5 to 40 days after the demo day (boarding lasts 2 to 6 nights; other services take one day);
- a message in the pet parent's words;
- a certificate scenario.

The same seed SHALL always give the same request and certificate, including after it has been sent.

#### Scenario: Same seed, same request
- **WHEN** a request is generated twice with seed 42, once before and once after sending it
- **THEN** both are identical, and both certificate images are byte-for-byte equal

#### Scenario: Seeds vary the request
- **WHEN** requests are generated for seeds 1 to 80
- **THEN** they include many pet names, both species, more than one service, and every scenario

### Requirement: The certificate matches its request
The certificate SHALL name the pet, its species and breed, and its owner, and list the vaccines required for the service and species, dated by its scenario:
- `current`: all given before the stay and expiring after it;
- `expired`: one expired before the stay;
- `expires_during_stay`: one expires on a day of the stay before checkout;
- `missing`: one is left off the card.

The scenario SHALL be described in plain words with the request.

#### Scenario: Matching pet and owner
- **WHEN** a request is generated
- **THEN** its certificate names the generated pet, its breed, and a seeded owner

#### Scenario: Scenario dates
- **WHEN** requests are generated for each scenario
- **THEN** the changed vaccine's dates on the card, or its absence, match the scenario's description

### Requirement: Scenarios hold with the records on file
The desk checks a card together with the pet's records on file. A generated pet is new and has none, so the scenario SHALL hold for the card alone and for the combined check.

#### Scenario: A record on file would cover the card
- **WHEN** requests are generated for seeds 1 to 80
- **THEN** checking each card together with its pet's records on file (none for a new pet) gives `compliant` for `current`, and otherwise exactly one failing vaccine with that scenario's status

### Requirement: Certificates can be viewed before sending
The API SHALL serve a generated request's certificate, and each fixed sample's certificate, as a PNG image. An unknown sample, or a sample without a certificate, SHALL get 404.

#### Scenario: Generated certificate image
- **WHEN** the certificate for seed 42 is requested
- **THEN** a PNG is returned, equal to the image that would be attached when sending seed 42

#### Scenario: Sample without a certificate
- **WHEN** the certificate for the unknown-pet sample is requested
- **THEN** the API answers 404

### Requirement: A generated request runs like a sample
Sending a generated request by its seed (optionally with edited message text) SHALL store it with its certificate attached and process it in the background, exactly like a sample.

#### Scenario: Send a generated request
- **WHEN** seed 42 is sent
- **THEN** a request is stored for the generated owner with the generated certificate attached, its id is returned at once, and it is later processed

### Requirement: Generated pets are new
The generator SHALL invent the request's pet for a seeded owner: a species, a name from a pool of at least 100 dog names and 50 cat names, a breed, and a weight that fits the breed. No pool name SHALL be a seeded pet's name or appear in a fixed sample's message. Sending SHALL add the pet to its owner before storing the request, or reuse that owner's pet with the same name.

#### Scenario: Send adds the pet
- **WHEN** seed 42 is sent
- **THEN** the owner has a pet with the generated name, species, breed, and weight, and intake can match the request to it

#### Scenario: Same seed sent twice
- **WHEN** seed 42 is sent twice
- **THEN** both requests belong to one pet

#### Scenario: The pool stays clear of other names
- **WHEN** the name pool is checked
- **THEN** it has at least 100 dog names and 50 cat names, no duplicates, no seeded pet's name, and no name from a sample's message

### Requirement: New names avoid names in use
When the server picks the seed, it SHALL skip any draw whose pet name matches, ignoring case, a pet on file or one of up to 20 recent names sent by the client. After 200 draws without a fresh name it SHALL use the last draw. A seed given by the client SHALL be used as is.

#### Scenario: A name on file is skipped
- **WHEN** a request is generated without a seed after a pet named Juno is on file
- **THEN** the generated pet is not named Juno

#### Scenario: Recent names are skipped
- **WHEN** a request is generated without a seed and with recent names
- **THEN** the generated pet's name is none of them

#### Scenario: A given seed is kept
- **WHEN** a request is generated with seed 42 and recent names that include seed 42's pet name
- **THEN** the request for seed 42 is returned unchanged

### Requirement: Previews carry their pet's photo fields
A generated request SHALL carry a pet id derived from its seed, and sending SHALL give the new pet that id. The demo samples list SHALL give each sample's pet id, species, and breed when the pet is on file, and none of them otherwise.

#### Scenario: The seed fixes the pet id
- **WHEN** seed 42 is previewed twice and then sent
- **THEN** both previews carry the same pet id, and the pet added on send has that id

#### Scenario: Sample pet fields
- **WHEN** the demo samples are listed
- **THEN** the clean boarding sample carries Biscuit's id, species, and breed, and the unknown-pet sample carries none
