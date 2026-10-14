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

## MODIFIED Requirements

### Requirement: Spans are recorded while work runs
A span SHALL be stored with status `running` when its work starts. When the work ends, the span SHALL be updated with its end time and status `ok` and its output, or status `error` and the error message. When the work raises an exception, including when it is cancelled, the span SHALL record the error, and the exception SHALL still reach the caller unchanged.

#### Scenario: Running span is visible
- **WHEN** a span has started and its work has not finished
- **THEN** a separate database connection can read the span with status `running` and no end time

#### Scenario: Failing work
- **WHEN** the work inside a span raises an exception
- **THEN** the span has status `error`, an end time, and the error message, and the same exception reaches the caller

#### Scenario: Cancelled work
- **WHEN** the task running the work inside a span is cancelled
- **THEN** the span has status `error` naming the cancellation, not `ok`, and the cancellation reaches the caller
