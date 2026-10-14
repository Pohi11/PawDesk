# Spec Delta

## ADDED Requirements

### Requirement: Abandoned spans are closed
When a booking request is processed again, spans from its earlier traces that are still `running` SHALL be closed with status `error`, an end time, and an error saying the process stopped before the work finished. Earlier traces still open SHALL be given an end time.

#### Scenario: Process killed mid-call
- **WHEN** an earlier run of a request left a span `running`, and the request is processed again
- **THEN** that span becomes `error` with an "abandoned" message and an end time, and its trace gets an end time

#### Scenario: Finished spans untouched
- **WHEN** a request is processed again
- **THEN** spans from earlier runs that already finished keep their status and end time
