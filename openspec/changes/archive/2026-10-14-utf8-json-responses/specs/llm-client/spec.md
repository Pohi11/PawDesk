# Spec Delta

## ADDED Requirements

### Requirement: Model text keeps its characters
Non-ASCII text in a model response (in the message or in tool-call arguments), sent as UTF-8 with or without a declared charset, SHALL reach the span, the saved step output, and recordings unchanged.

#### Scenario: An en dash in a tool call
- **WHEN** the resolver's model proposes an offer whose summary contains an en dash, sent as raw UTF-8 with no charset
- **THEN** the saved resolution step and its span hold the summary with the en dash unchanged

#### Scenario: An en dash through a recording
- **WHEN** a response containing an en dash is recorded and the same call is replayed
- **THEN** the replayed text has the en dash unchanged
