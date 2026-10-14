# Spec Delta

## Purpose

Lets staff see the requests waiting for review and approve, edit and approve, or reject them. Each action is recorded and resumes the run.

## ADDED Requirements

### Requirement: Staff can see the review queue
The API SHALL list the requests in `needs_review`, oldest first, each with its owner, pet, service, dates, flag reasons, and drafted reply.

#### Scenario: Queue lists waiting requests
- **WHEN** one request is in `needs_review` and another has been sent
- **THEN** the queue lists only the waiting request, with its flag reasons and draft

### Requirement: Staff decide flagged requests
The API SHALL accept three actions on a request in `needs_review`, each with the staff member's name:
- approve: the drafted reply is sent;
- edit and approve: the staff member's text is sent instead;
- reject: a reason is required, and a decline is sent.

Each action SHALL record an Approval and move the request in one transaction, and then resume processing until the request is `sent`. An action on a request that is not in `needs_review` SHALL be refused with HTTP 409 and change nothing.

#### Scenario: Approve
- **WHEN** staff approve a flagged request
- **THEN** an Approval is recorded, the request ends in `sent`, and the outbound message is the drafted reply

#### Scenario: Edit and approve
- **WHEN** staff edit the reply and approve
- **THEN** the outbound message is the staff member's text

#### Scenario: Reject with a reason
- **WHEN** staff reject a flagged request with a reason
- **THEN** the request ends in `sent` with a decline as the outbound message, and the reason is recorded on the Approval but not sent

#### Scenario: Reject without a reason
- **WHEN** staff reject without a reason
- **THEN** the API refuses with HTTP 422 and nothing changes

#### Scenario: Acting twice
- **WHEN** staff approve a request that was already approved
- **THEN** the API refuses with HTTP 409 and no second Approval is recorded
