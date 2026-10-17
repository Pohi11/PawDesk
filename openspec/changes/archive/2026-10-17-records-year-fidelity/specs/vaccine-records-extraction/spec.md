# Spec Delta

## ADDED Requirements

### Requirement: Printed dates are copied exactly
The records step's instructions SHALL tell the model to copy every date given and expiry exactly as printed, year included, and SHALL say that dates later than today are expected and must not be moved toward today. Any change to the instructions' wording SHALL change the recorded prompt version.

#### Scenario: Prompt keeps printed years
- **WHEN** the records step calls the model
- **THEN** the instructions tell the model to copy each date's year exactly as printed and not to adjust a date because it is later than today

#### Scenario: Prompt version recorded
- **WHEN** a certificate is processed
- **THEN** the `records` span records prompt version `records-v2`
