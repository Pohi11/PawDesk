# Spec Delta

## Purpose

Reads a vaccine certificate image into validated vaccine records for the compliance check, and decides in code when the extraction is too doubtful to use without a person looking.

## ADDED Requirements

### Requirement: Extraction returns validated records
The records step SHALL return:
- the pet name as printed on the certificate (or empty);
- a list of records, each with the label as written, the vaccine it maps to (or empty when it maps to none), the date given, and the expiry date (or empty);
- whether the image was readable;
- a confidence from 0 to 1;
- a list of ambiguities.

Model output that doesn't fit this shape SHALL NOT be used. It SHALL get exactly one repair attempt carrying the validation errors.

#### Scenario: Readable certificate
- **WHEN** the model returns valid output for a certificate listing rabies and DHPP
- **THEN** the step returns two records with their labels, vaccines, and dates

#### Scenario: Invalid output repaired once
- **WHEN** the first output is invalid and the repair output is valid
- **THEN** the step returns the repaired records after exactly two model calls

#### Scenario: Invalid twice
- **WHEN** both outputs are invalid
- **THEN** the step fails with an invalid-output error after exactly two model calls

### Requirement: Records feed compliance unchanged
Every record that maps to a known vaccine SHALL be returned as the same vaccine-evidence value the compliance check accepts, with the date given and the expiry date exactly as extracted.

#### Scenario: Records drive compliance
- **WHEN** extraction returns rabies given 2026-04-01 expiring 2027-04-01
- **THEN** that record, passed to the compliance check, makes rabies `ok` for a stay in March 2027

### Requirement: Expiry dates are never inferred
When a certificate doesn't print an expiry date, the extracted expiry SHALL be empty. It SHALL NOT be computed from the date given, a typical vaccine duration, or anything else.

#### Scenario: No expiry printed
- **WHEN** the model returns a record with no expiry date
- **THEN** the returned record's expiry is empty, and compliance reports that vaccine as `unknown_expiry` when no other record covers the stay

#### Scenario: Prompt forbids inference
- **WHEN** the records step calls the model
- **THEN** the instructions tell the model to leave the expiry empty when it isn't printed and never to estimate it

### Requirement: Only acceptable images reach the model
Only PNG, JPEG, or WebP images of at most 5 MB SHALL be sent to the model. Any other input SHALL be refused before any model call, with the outcome `needs_review` and an issue explaining why.

#### Scenario: Oversized image
- **WHEN** a 6 MB image is submitted
- **THEN** no model call is made and the outcome is `needs_review`

#### Scenario: Unsupported type
- **WHEN** a PDF is submitted
- **THEN** no model call is made and the outcome is `needs_review`

### Requirement: Extracted records are checked in code
After parsing, the records step SHALL report an issue when:
- a record's date given is after the facility's current date;
- a record's expiry is before its date given;
- a record's label maps to no known vaccine;
- the certificate's pet name doesn't match the pet being booked (case-insensitive, surrounding whitespace ignored);
- no records were found.

#### Scenario: Future administration date
- **WHEN** today is 2027-03-03 and a record says it was given 2027-05-01
- **THEN** the step reports a date issue for that record

#### Scenario: Expiry before administration
- **WHEN** a record says given 2026-05-01 and expiring 2026-04-01
- **THEN** the step reports a date issue for that record

#### Scenario: Unknown vaccine label
- **WHEN** a record's label is "Lyme" and it maps to no known vaccine
- **THEN** the step reports an unknown-vaccine issue and does not pass that record to compliance

#### Scenario: Certificate for another pet
- **WHEN** the certificate names "Max" and the pet being booked is Biscuit
- **THEN** the step reports a pet-name issue

#### Scenario: Matching pet name
- **WHEN** the certificate names "BISCUIT " and the pet is Biscuit
- **THEN** no pet-name issue is reported

### Requirement: Doubtful extractions go to a person
The step SHALL report an issue when the model says the image isn't readable, when confidence is below 0.7, or when the model lists any ambiguity. The outcome SHALL be `needs_review` when any issue exists, and `clear` otherwise.

#### Scenario: Unreadable image
- **WHEN** the model reports the image is not readable
- **THEN** the outcome is `needs_review`

#### Scenario: Clean extraction
- **WHEN** the image is readable, confidence is 0.9, there are no ambiguities, and every check passes
- **THEN** the outcome is `clear`

### Requirement: Extraction is traced without storing the image
Each run SHALL record a `code` span named `records`, with its model calls as child `llm` spans. The image SHALL appear in stored spans only as its SHA-256 hash and size. The `records` span SHALL record the prompt version, the image hash, and the outcome.

#### Scenario: Traced run
- **WHEN** a certificate is processed
- **THEN** the trace has a `records` span with a child `llm` span, and no stored span contains the image's base64 data
