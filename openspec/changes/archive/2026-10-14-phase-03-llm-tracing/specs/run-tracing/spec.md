# Spec Delta

## ADDED Requirements

### Requirement: Spans are recorded while work runs
A span SHALL be stored with status `running` when its work starts. When the work ends, the span SHALL be updated with its end time and status `ok` and its output, or status `error` and the error message. When the work raises an exception, the span SHALL record the error, and the exception SHALL still reach the caller unchanged.

#### Scenario: Running span is visible
- **WHEN** a span has started and its work has not finished
- **THEN** a separate database connection can read the span with status `running` and no end time

#### Scenario: Failing work
- **WHEN** the work inside a span raises an exception
- **THEN** the span has status `error`, an end time, and the error message, and the same exception reaches the caller

### Requirement: Parent links follow the code structure
A span opened while another span is active SHALL record that span as its parent. Spans opened by work running concurrently under the same parent SHALL each record that parent and SHALL NOT become each other's parents.

#### Scenario: Nested work
- **WHEN** a span is opened inside another span
- **THEN** the inner span's parent is the outer span

#### Scenario: Concurrent siblings
- **WHEN** two spans are opened by work running concurrently inside the same parent span
- **THEN** both have that parent and neither is the parent of the other

### Requirement: Traces survive rolled-back work
Traces and spans SHALL be committed independently of the business transaction they describe, so that a span remains stored when that transaction is rolled back.

#### Scenario: Business transaction rolls back
- **WHEN** work inside a span writes to the database, fails, and its transaction is rolled back
- **THEN** the business writes are gone and the span remains with status `error`

### Requirement: Spans carry attributes
Every span SHALL have an attributes field holding a JSON object, empty by default, for structured metadata such as attempts, finish reason, provider, and request parameters.

#### Scenario: Default attributes
- **WHEN** a span is stored without attributes
- **THEN** its attributes are an empty JSON object

#### Scenario: Attributes round-trip
- **WHEN** a span is stored with attributes `{"finish_reason": "stop", "attempts": [{"n": 1, "outcome": "ok"}]}`
- **THEN** reading it back returns the same attributes
