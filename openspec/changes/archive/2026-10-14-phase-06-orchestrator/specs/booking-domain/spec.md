# Spec Delta

## ADDED Requirements

### Requirement: A booking request can carry a certificate image
A booking request SHALL be able to store one certificate image, kept together with its SHA-256 hash, MIME type, and size in bytes. Only PNG, JPEG, or WebP images of at most 5 MB SHALL be stored. The type SHALL be determined from the file's contents, not its name.

#### Scenario: Image stored with its hash
- **WHEN** a PNG certificate is attached to a request
- **THEN** it can be read back unchanged, with its SHA-256 hash, type `image/png`, and size

#### Scenario: Second certificate rejected
- **WHEN** a second certificate is attached to the same request
- **THEN** the database rejects it

#### Scenario: Unsupported file refused
- **WHEN** a PDF is attached to a request
- **THEN** it is refused before anything is stored
