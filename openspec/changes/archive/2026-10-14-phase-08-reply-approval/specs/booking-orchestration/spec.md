# Spec Delta

## ADDED Requirements

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
- **WHEN** a request that has already reached `sent` is processed again
- **THEN** nothing changes and no model is called
