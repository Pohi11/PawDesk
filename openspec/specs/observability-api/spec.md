# observability-api Specification

## Purpose
Gives operators read-only HTTP access to everything PawDesk records about its runs (requests, steps, spans, metrics, and eval reports), streams a run's progress live, and accepts demo submissions.

## Requirements

### Requirement: Requests can be listed and inspected
The API SHALL list recent requests, newest first, with their state, owner, pet, service, dates, total model cost, and whether they were flagged. For one request, it SHALL return the request, its transitions in order, its saved step results, its approvals, its outbound message, and every trace with all its spans (kind, status, timing, model, tokens, cost, input, output, attributes, error).

#### Scenario: List shows cost and flag
- **WHEN** one request was sent automatically and another is waiting for review
- **THEN** the list shows both, with each one's total cost, and only the waiting one flagged

#### Scenario: Detail shows the whole run
- **WHEN** a processed request is inspected
- **THEN** the response includes its transitions in order, its step results, and its trace's spans with parent links and timings

#### Scenario: Unknown request
- **WHEN** an unknown request id is inspected
- **THEN** the API answers 404

### Requirement: Run progress streams as server-sent events
The API SHALL stream a request's progress as `text/event-stream`. It SHALL send a snapshot (state and spans) when the stream opens and whenever the state or any span changes. It SHALL end the stream once the request is resting (`sent`, `needs_review`, or `failed`) with no running span, or after a time limit.

#### Scenario: Progress then end
- **WHEN** a client subscribes to a request that is then processed to `sent`
- **THEN** it receives at least one snapshot showing a running span or an intermediate state, a final snapshot in `sent`, and the stream ends

#### Scenario: Resting request
- **WHEN** a client subscribes to a request already in `sent`
- **THEN** it receives one snapshot and the stream ends

### Requirement: Metrics summarize cost, latency, and flags
The API SHALL report:
- requests per state;
- the total and average model cost per request;
- the cost and call count per model step;
- the median and 95th-percentile run duration;
- the share of drafted requests that were flagged for review.

#### Scenario: Cost per step
- **WHEN** two requests each made one intake call costing $0.001
- **THEN** the intake step shows 2 calls and $0.002

#### Scenario: Flag rate
- **WHEN** three requests were drafted and one of them went to review
- **THEN** the flag rate is one in three

### Requirement: Eval reports are listed over time
The API SHALL list every saved evaluation report, oldest first, with its kind (intake or records), benchmark version, prompt version, model, date, cost, and headline numbers.

#### Scenario: Reports listed
- **WHEN** the results folder holds an intake report and a records report
- **THEN** both are listed in date order with their headline numbers

### Requirement: Demo requests run in the background
The API SHALL list sample requests, including at least one injection attempt. It SHALL accept a sample (optionally with edited message text), store it as a new request for that sample's owner (with its certificate image, if any), and return the request id immediately. Processing SHALL run in the background.

#### Scenario: Submit a sample
- **WHEN** the injection sample is submitted
- **THEN** the API returns a new request id at once, and the request is later processed

#### Scenario: Unknown sample
- **WHEN** a sample id that doesn't exist is submitted
- **THEN** the API answers 404 and stores nothing

### Requirement: Requests identify the matched pet
The request list and the request detail SHALL report the matched pet's id, species, and breed alongside its name. When no pet is matched, all four SHALL be null.

#### Scenario: Matched pet
- **WHEN** a request matched to Biscuit, a dog whose breed is "Beagle", is listed and inspected
- **THEN** both responses include Biscuit's pet id, species `dog`, and breed `Beagle`

#### Scenario: No matched pet
- **WHEN** a request with no matched pet is listed and inspected
- **THEN** both responses report the pet's name, id, species, and breed as null

### Requirement: JSON responses declare UTF-8
Every JSON response from the API SHALL be encoded as UTF-8 and declared as `application/json; charset=utf-8`, so clients that guess an encoding when none is given read non-ASCII text correctly.

#### Scenario: Non-ASCII text in a response
- **WHEN** a request whose resolver summary contains an en dash is inspected
- **THEN** the response is declared `application/json; charset=utf-8`, and the summary reads back with the en dash unchanged

#### Scenario: Error responses too
- **WHEN** an unknown request id is inspected, or a demo submission fails validation
- **THEN** the error response is declared `application/json; charset=utf-8`
