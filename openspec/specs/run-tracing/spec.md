# run-tracing Specification

## Purpose

Stores a complete record of every run as a trace made of spans, modeled on OpenTelemetry, so each step's inputs, outputs, timing, token usage, cost, and errors can be inspected afterward.

## Requirements

### Requirement: A trace groups the spans of one run
A trace SHALL have an identifier, a name, a start time, and optionally an end time and the booking request it belongs to. Every span SHALL belong to exactly one trace.

#### Scenario: Span without a trace is rejected
- **WHEN** a span is stored without a trace
- **THEN** the database rejects the record

### Requirement: Spans form a tree within their trace
A span MAY have a parent span. A parent span SHALL belong to the same trace as its child.

#### Scenario: Nested span is stored
- **WHEN** a span is stored with a parent span from the same trace
- **THEN** both spans can be read back with the parent link intact

#### Scenario: Parent from another trace is rejected
- **WHEN** a span is stored with a parent span from a different trace
- **THEN** the database rejects the record

### Requirement: Spans have a kind and a status
Every span SHALL have a kind of `llm`, `tool`, `code`, or `human`, and a status of `running`, `ok`, or `error`. A span with status `error` SHALL include an error message.

#### Scenario: Unknown kind is rejected
- **WHEN** a span is stored with kind `agent`
- **THEN** the database rejects the record

#### Scenario: Error span without a message is rejected
- **WHEN** a span is stored with status `error` and no error message
- **THEN** the database rejects the record

### Requirement: Spans store payloads, timing, and usage
A span SHALL be able to store structured input and output, start and end times, and, for model calls, the model name, prompt tokens, completion tokens, and cost in US dollars. Token counts and cost SHALL NOT be negative, and the end time SHALL NOT be before the start time.

#### Scenario: Model-call span round-trips
- **WHEN** an `llm` span is stored with model, 42 prompt tokens, 68 completion tokens, a cost of 0.0000942, and JSON input and output
- **THEN** reading it back returns the same values, with the cost exact to at least 8 decimal places

#### Scenario: Negative token count is rejected
- **WHEN** a span is stored with -1 prompt tokens
- **THEN** the database rejects the record

#### Scenario: End before start is rejected
- **WHEN** a span is stored with an end time earlier than its start time
- **THEN** the database rejects the record

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
