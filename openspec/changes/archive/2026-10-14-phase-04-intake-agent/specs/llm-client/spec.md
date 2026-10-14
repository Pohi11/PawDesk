# Spec Delta

## ADDED Requirements

### Requirement: Structured requests go only to endpoints that support them
When a model call requests a response format, the request SHALL ask the provider to route only to endpoints that support every requested parameter. When no response format is requested, the request SHALL carry no such routing restriction.

#### Scenario: Response format requested
- **WHEN** a model call includes a JSON-schema response format
- **THEN** the request body asks the provider to require support for all requested parameters

#### Scenario: Plain request
- **WHEN** a model call has no response format
- **THEN** the request body contains no provider routing preferences
