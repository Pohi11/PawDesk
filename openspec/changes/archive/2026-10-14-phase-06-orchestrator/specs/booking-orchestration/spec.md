# Spec Delta

## Purpose

Drives a booking request through extraction and checks in a fixed order, saves every step durably so a crashed run resumes without repeating finished work, and routes the request to the next stage with explicit reasons.

## ADDED Requirements

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
- **THEN** the checks and routing complete, and no model is called during the second run

#### Scenario: Crash during extraction
- **WHEN** a run stops after the move to `extracting` but before the extraction results are saved, and the request is processed again
- **THEN** extraction runs again, and the request ends with exactly one saved result per step

#### Scenario: Finished request
- **WHEN** a request that has already reached `drafting` or `resolving` is processed again
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
