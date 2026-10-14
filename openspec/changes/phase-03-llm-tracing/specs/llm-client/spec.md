# Spec Delta

## Purpose

Defines the single way the system calls a language model, so that every call is traced, bounded in time, retried only when retrying can help, charged at the provider's reported cost, and recorded without secrets.

## ADDED Requirements

### Requirement: Model calls require an active trace
A model call SHALL be refused, without contacting the provider, when no trace is active.

#### Scenario: Call outside a trace
- **WHEN** a model call is made with no active trace
- **THEN** it fails with an error and no request is sent to the provider

### Requirement: Each call records one model span
Each model call SHALL record exactly one span of kind `llm`, whatever the number of attempts. The span SHALL hold the request messages, the requested model and parameters, the response text, the model that answered, prompt and completion token counts, start and end times, the finish reason, the provider's generation id, and one attempt entry per attempt made.

#### Scenario: Successful call
- **WHEN** a model call succeeds on its first attempt
- **THEN** one `llm` span with status `ok` holds the messages, response text, model, token counts, finish reason, generation id, and a single attempt entry

#### Scenario: Call that needed a retry
- **WHEN** a model call fails once with a 429 and then succeeds
- **THEN** one `llm` span with status `ok` records two attempts, the first marked as a 429

### Requirement: Cost comes from the provider, never estimated
A span's cost SHALL be the cost the provider reported for the call, stored exactly. When the provider reports no cost, the cost SHALL be left empty rather than estimated.

#### Scenario: Reported cost is stored exactly
- **WHEN** the provider reports a cost of 0.0000942
- **THEN** the span's cost is exactly 0.0000942

#### Scenario: Missing cost stays empty
- **WHEN** the provider's response contains no cost
- **THEN** the span's cost is empty and the call still succeeds

### Requirement: Transient failures are retried with backoff
A call SHALL be retried when an attempt times out, cannot connect, or receives status 408, 429, 500, 502, 503, or 504. It SHALL make at most the configured number of attempts (3 by default). Between attempts it SHALL wait for the `Retry-After` duration when one is given, and otherwise for a randomized, exponentially growing delay.

#### Scenario: Rate limited, then succeeds
- **WHEN** the first attempt receives 429 and the second succeeds
- **THEN** the call returns the second attempt's response

#### Scenario: Retry-After is honored
- **WHEN** an attempt receives 429 with `Retry-After: 2`
- **THEN** the next attempt starts no sooner than 2 seconds later

#### Scenario: Attempts run out
- **WHEN** every attempt receives 503
- **THEN** the call fails after exactly the configured number of attempts and its span has status `error`

#### Scenario: Timeout is retried
- **WHEN** the first attempt times out and the second succeeds
- **THEN** the call returns the second attempt's response

### Requirement: Permanent failures are not retried
A call SHALL fail immediately, without retrying, when an attempt receives status 400, 401, 402, or 403.

#### Scenario: Invalid key
- **WHEN** an attempt receives 401
- **THEN** the call fails after one attempt and its span has status `error`

#### Scenario: Out of credits
- **WHEN** an attempt receives 402
- **THEN** the call fails after one attempt

### Requirement: An error inside a successful response is a failure
A response with status 200 whose body carries an error and no answer SHALL be treated as a failed attempt. It SHALL be retried only if the error's code is one of the transient statuses.

#### Scenario: 200 with a provider error
- **WHEN** an attempt receives status 200 with an error body of code 502 and the next attempt succeeds
- **THEN** the call returns the second attempt's response and records the first as failed

### Requirement: Each attempt has a timeout
Each attempt SHALL be bounded by the configured timeout (30 seconds by default), so one slow attempt can't hold a run indefinitely.

#### Scenario: Slow attempt
- **WHEN** an attempt takes longer than the configured timeout
- **THEN** that attempt is abandoned and counted as a timeout

### Requirement: Secrets and raw images are never recorded
The API key and request headers SHALL never be stored in any trace or span. Inline image data in request messages SHALL be stored only as a placeholder holding the data's SHA-256 hash and size in bytes.

#### Scenario: Key never reaches the database
- **WHEN** a model call is recorded, whether it succeeds or fails
- **THEN** no stored trace or span contains the API key

#### Scenario: Image replaced by its hash
- **WHEN** a request message contains an inline base64 image
- **THEN** the span's recorded messages contain the image's SHA-256 hash and byte size instead of the image data
