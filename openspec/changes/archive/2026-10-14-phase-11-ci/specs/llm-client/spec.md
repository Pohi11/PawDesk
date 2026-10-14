# Spec Delta

## ADDED Requirements

### Requirement: Model responses can be recorded and replayed
The model client SHALL support three modes:
- `off` (default): calls the model;
- `record`: calls the model and saves each successful response under a hash of the exact request body;
- `replay`: answers only from saved responses and never opens a network connection.

In replay mode, a request with no saved response SHALL fail as a permanent error naming the missing recording.

#### Scenario: Record then replay
- **WHEN** a call is made in record mode and the same call is made again in replay mode
- **THEN** the replayed call returns the same response without contacting the model

#### Scenario: Missing recording
- **WHEN** a call is made in replay mode with no saved response for its request
- **THEN** it fails without retrying, and the error names the missing recording
