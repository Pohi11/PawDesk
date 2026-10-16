# booking-orchestration Specification

## Purpose
Drives a booking request through extraction and checks in a fixed order, saves every step durably so a crashed run resumes without repeating finished work, and routes the request to the next stage with explicit reasons.

## Requirements

### Requirement: Extraction runs intake and records concurrently
When a request is processed, the intake step and the records step SHALL both start before either finishes. The request SHALL move from `received` to `extracting` before they start, and to `checking` only after both results are saved.

#### Scenario: Both start before either ends
- **WHEN** a request with a message and a certificate is processed and each model call takes a measurable time
- **THEN** both extraction spans start before either of them ends

#### Scenario: Request without a certificate
- **WHEN** a request has no certificate image
- **THEN** intake runs, the records step is skipped with a "no certificate provided" reason, and the request still reaches `checking`

### Requirement: Each step is saved with its state change
Each step's result SHALL be saved in the same transaction as the state change that follows it. A request SHALL have at most one saved result per step.

#### Scenario: Result and state together
- **WHEN** the extraction step completes
- **THEN** the intake and records results and the move to `checking` are all saved, or none of them are

#### Scenario: One result per step
- **WHEN** a second result for the same request and step is stored
- **THEN** the database rejects it

### Requirement: A crashed run resumes without repeating finished work
Processing a request SHALL continue from its current state, using saved step results. It SHALL NOT call a model again for any step whose result is already saved.

#### Scenario: Crash after extraction
- **WHEN** a run stops after the extraction results are saved, and the request is processed again
- **THEN** the checks and routing complete, and no extraction model call is made during the second run

#### Scenario: Crash during extraction
- **WHEN** a run stops after the move to `extracting` but before the extraction results are saved, and the request is processed again
- **THEN** extraction runs again, and the request ends with exactly one saved result per step

#### Scenario: Finished request
- **WHEN** a request that has already reached `sent` is processed again
- **THEN** nothing changes and no model is called

### Requirement: Checks combine every source
The checking step SHALL:
- compare the pet name on the certificate with the pet intake matched;
- check vaccine compliance for the requested service and dates, using the pet's records on file together with the records extracted from the certificate;
- for boarding, look for a free kennel of the pet's size class.

Daycare and grooming SHALL need no kennel.

#### Scenario: Extracted records complete what is on file
- **WHEN** the pet's records on file lack bordetella and the certificate provides a covering bordetella record
- **THEN** compliance treats bordetella as covered

#### Scenario: Certificate for another pet
- **WHEN** intake matched Biscuit but the certificate names Max
- **THEN** the checks report a pet-name mismatch

#### Scenario: No kennel needed for grooming
- **WHEN** the request is for grooming
- **THEN** no kennel search is made and capacity is reported as not needed

### Requirement: Routing is decided by code with reasons
After checking, the request SHALL move to `drafting` only when:
- intake is clear, and records are clear or were skipped because no certificate was sent;
- a pet is matched;
- compliance is `compliant`;
- a kennel was found or none is needed.

Otherwise it SHALL move to `resolving`, and the saved routing result SHALL list every reason.

#### Scenario: Everything clear
- **WHEN** all extraction and checks are clear for a boarding request with a free kennel
- **THEN** the request moves to `drafting` with no reasons

#### Scenario: Several problems
- **WHEN** a vaccine expires during the stay and no kennel is free
- **THEN** the request moves to `resolving`, and the reasons name both the vaccine and the capacity problem

#### Scenario: No certificate, records on file cover the stay
- **WHEN** a request has no certificate and the pet's records on file cover every required vaccine
- **THEN** the request moves to `drafting`

#### Scenario: No pet matched
- **WHEN** intake could not match a pet
- **THEN** compliance and capacity are not checked, and the request moves to `resolving` with a reason saying the pet is unknown

### Requirement: Step failures are recorded and retried
When a step fails because a model call fails or its output stays invalid after repair, the request SHALL move to `failed` with the error. Processing a failed request SHALL retry from the failed step.

#### Scenario: Model unavailable during extraction
- **WHEN** every model attempt during extraction fails
- **THEN** the request is `failed` with the failed step `extracting` and the error recorded

#### Scenario: Retry after failure
- **WHEN** a request failed during extraction and is processed again while the model is available
- **THEN** it returns to `extracting`, completes, and reaches routing

### Requirement: Each run is traced and linked to its request
Each processing run SHALL record a trace linked to the booking request, with spans for extraction, checks, and routing, and the model calls nested under their steps.

#### Scenario: Traced run
- **WHEN** a request is processed from `received` to routing
- **THEN** its trace is linked to the request and contains `extract`, `check`, and `route` spans, with the `intake` and `records` spans under `extract`

### Requirement: Resolving runs the resolver, then moves to drafting
Processing a request in `resolving` SHALL run the resolution step and save its result (outcome, reason, proposal, and the tool calls made) in the same transaction as the move to `drafting`. A model failure during resolution SHALL move the request to `failed` with the failed step `resolving`, and processing it again SHALL retry the resolution.

#### Scenario: Resolution saved with the move
- **WHEN** a request in `resolving` is processed and the resolver proposes an offer
- **THEN** the request is in `drafting` and its saved `resolution` result contains the proposal

#### Scenario: Not attempted still moves on
- **WHEN** a request in `resolving` has a problem only a person can handle
- **THEN** it moves to `drafting` with a `not_attempted` resolution, and no model is called

#### Scenario: Model unavailable during resolution
- **WHEN** every model attempt during resolution fails
- **THEN** the request is `failed` with the failed step `resolving`, and processing it again retries the resolution

### Requirement: Clean requests are approved and sent without waiting
Processing SHALL continue past drafting:
- a request in `ready` SHALL be approved by the system;
- a request in `approved` or `rejected` SHALL be sent.

Sending SHALL record exactly one outbound message per request, in the same transaction as the move to `sent`. For a confirmed boarding request, sending SHALL also reserve a free kennel of the pet's size class in that transaction. If no kennel is free any more, the request SHALL move to `failed` without a reservation or a message.

#### Scenario: Clean boarding request runs to sent
- **WHEN** a clean boarding request is processed
- **THEN** it ends in `sent`, with one reservation for the stay and one outbound message containing the drafted reply

#### Scenario: Kennel taken before sending
- **WHEN** the last free kennel is reserved by someone else between drafting and sending
- **THEN** the request is `failed` with the failed step `approved`, and no reservation or message is recorded for it

#### Scenario: Waiting request is left alone
- **WHEN** a request in `needs_review` is processed
- **THEN** nothing changes and no model is called

### Requirement: A pet already booked for the stay is not booked again
For boarding, the capacity check SHALL first look for a reservation of the same pet that shares a night with the stay. If one exists, no kennel SHALL be searched, capacity SHALL be reported as already booked, and the request SHALL move to `resolving` with the reason "capacity: <pet> already has a kennel for these nights". The resolver SHALL treat it as a problem that needs a person.

#### Scenario: Same pet, same nights
- **WHEN** Biscuit holds a kennel for Mar 24 to Mar 27 and a boarding request for Biscuit for Mar 24 to Mar 27 is checked, while medium kennels are free
- **THEN** capacity reports already booked with no kennel, the request moves to `resolving` with the reason "capacity: Biscuit already has a kennel for these nights", and the resolution is `not_attempted`

#### Scenario: Another pet's stay does not count
- **WHEN** Rosie holds a medium kennel for Mar 24 to Mar 27 and a boarding request for Biscuit for the same nights is checked, while another medium kennel is free
- **THEN** capacity reports a kennel found

### Requirement: Sending checks the pet again
Before reserving a kennel for a confirmed boarding request, sending SHALL check again that the pet has no reservation sharing a night with the stay. If it has one, the request SHALL move to `failed` without a reservation or a message.

#### Scenario: Pet booked before sending
- **WHEN** a clean boarding request for Biscuit is drafted, and Biscuit is reserved for the same nights before it is sent
- **THEN** the request is `failed` with the failed step `approved`, and no reservation or message is recorded for it
