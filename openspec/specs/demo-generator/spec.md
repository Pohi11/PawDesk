# demo-generator Specification

## Purpose
Makes up demo booking requests on the spot, each with a vaccine certificate that matches it, so the desk can be shown handling requests it was never tuned on, and the certificate can be read by a person before the model reads it.

## Requirements

### Requirement: Random requests are reproducible
Given a seed, the generator SHALL produce a request for a seeded owner and one of their pets. The request SHALL include:
- a service the facility has vaccine rules for, for that species;
- a stay starting 5 to 40 days after the demo day (boarding lasts 2 to 6 nights; other services take one day);
- a message in the pet parent's words;
- a certificate scenario.

The same seed SHALL always give the same request and certificate.

#### Scenario: Same seed, same request
- **WHEN** a request is generated twice with seed 42
- **THEN** both are identical, and both certificate images are byte-for-byte equal

#### Scenario: Seeds vary the request
- **WHEN** requests are generated for seeds 1 to 40
- **THEN** they include more than one pet, more than one service, and every scenario

### Requirement: The certificate matches its request
The certificate SHALL name the request's pet and owner, and list the vaccines the facility requires for that service and species, dated by its scenario:
- `current`: every vaccine was given before the stay and expires after it;
- `expired`: one required vaccine expired before the stay;
- `expires_during_stay`: one required vaccine expires on a day of the stay before checkout;
- `missing`: one required vaccine is left off the card.

The scenario SHALL be described in plain words with the request.

#### Scenario: Matching pet and owner
- **WHEN** a request is generated for Biscuit
- **THEN** its certificate names Biscuit and Biscuit's owner

#### Scenario: Scenario dates
- **WHEN** requests are generated for each scenario
- **THEN** the changed vaccine's dates on the card, or its absence, match the scenario's description

### Requirement: Scenarios hold with the records on file
The desk checks a card together with the pet's records on file, so the generator SHALL change only a vaccine for which that combined check gives the scenario's status. When no draw of pet, service, and stay allows it, the request SHALL use `current`.

#### Scenario: A record on file would cover the card
- **WHEN** requests are generated for seeds 1 to 80
- **THEN** checking each card together with its pet's records on file gives `compliant` for `current`, and otherwise exactly one failing vaccine with that scenario's status

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
