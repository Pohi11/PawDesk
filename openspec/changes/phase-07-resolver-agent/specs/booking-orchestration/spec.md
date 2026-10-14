# Spec Delta

## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: A crashed run resumes without repeating finished work
Processing a request SHALL continue from its current state, using saved step results. It SHALL NOT call a model again for any step whose result is already saved.

#### Scenario: Crash after extraction
- **WHEN** a run stops after the extraction results are saved, and the request is processed again
- **THEN** the checks and routing complete, and no extraction model call is made during the second run

#### Scenario: Crash during extraction
- **WHEN** a run stops after the move to `extracting` but before the extraction results are saved, and the request is processed again
- **THEN** extraction runs again, and the request ends with exactly one saved result per step

#### Scenario: Finished request
- **WHEN** a request that has already reached `drafting` is processed again
- **THEN** nothing changes and no model is called
