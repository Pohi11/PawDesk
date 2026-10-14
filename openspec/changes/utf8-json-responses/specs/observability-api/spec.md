# Spec Delta

## ADDED Requirements

### Requirement: JSON responses declare UTF-8
Every JSON response from the API SHALL be encoded as UTF-8 and declared as `application/json; charset=utf-8`, so clients that guess an encoding when none is given read non-ASCII text correctly.

#### Scenario: Non-ASCII text in a response
- **WHEN** a request whose resolver summary contains an en dash is inspected
- **THEN** the response is declared `application/json; charset=utf-8`, and the summary reads back with the en dash unchanged
