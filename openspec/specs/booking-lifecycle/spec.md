# booking-lifecycle Specification

## Purpose

Governs how a booking request moves from receipt to a sent reply: which states exist, which transitions are allowed and by whom, how failures are recorded and retried, and how every change is audited and protected from concurrent updates.

## Requirements

### Requirement: Booking requests have exactly one lifecycle state
Every booking request SHALL be in exactly one of these states: `received`, `extracting`, `checking`, `resolving`, `drafting`, `needs_review`, `ready`, `approved`, `rejected`, `sent`, `failed`. A new request SHALL start in `received`.

#### Scenario: New request starts in received
- **WHEN** a booking request is created
- **THEN** its state is `received`

#### Scenario: Unknown state is rejected
- **WHEN** a booking request is stored with state `pending`
- **THEN** the database rejects the record

### Requirement: Only listed transitions are allowed
Every state change SHALL name an actor, either `system` or `staff`. A change SHALL succeed only if its (from, to, actor) combination is listed by the transition requirements in this spec. Any other combination SHALL be rejected with an error naming both states, and the request SHALL be left unchanged.

#### Scenario: Skipping ahead is rejected
- **WHEN** the system tries to move a request from `received` to `sent`
- **THEN** the transition is rejected with an error naming `received` and `sent`
- **AND** the request is still in `received`

#### Scenario: Leaving a terminal state is rejected
- **WHEN** anything tries to move a request out of `sent`
- **THEN** the transition is rejected

#### Scenario: Every unlisted combination is rejected
- **WHEN** each (from, to, actor) combination that is not listed in the table is attempted
- **THEN** every one of them is rejected

### Requirement: The system drives processing steps
Only the `system` actor SHALL move a request along the processing path: `received` → `extracting` → `checking`, then `checking` → `resolving` → `drafting` or `checking` → `drafting`, then `drafting` → `needs_review` or `drafting` → `ready`.

#### Scenario: Allowed processing transition succeeds
- **WHEN** the system moves a request from `checking` to `drafting`
- **THEN** the request's state becomes `drafting`

#### Scenario: Staff cannot drive processing
- **WHEN** staff tries to move a request from `received` to `extracting`
- **THEN** the transition is rejected

### Requirement: Decisions lead to approved or rejected
A request SHALL leave `ready` only to `approved` (by the system) or to `rejected` (by staff). A request SHALL leave `needs_review` only to `approved` or `rejected`, and only by staff.

#### Scenario: Staff rejects a clean request
- **WHEN** staff moves a request from `ready` to `rejected`
- **THEN** the request's state becomes `rejected`

#### Scenario: System cannot reject
- **WHEN** the system tries to move a request from `needs_review` to `rejected`
- **THEN** the transition is rejected

### Requirement: Decided requests are sent by the system
Only the `system` actor SHALL move a request from `approved` or `rejected` to `sent`. `sent` SHALL be terminal.

#### Scenario: Approved request is sent
- **WHEN** the system moves a request from `approved` to `sent`
- **THEN** the request's state becomes `sent`

### Requirement: Approval requires deterministic clearance or a person
A request SHALL enter `approved` only through the system from `ready`, or through staff from `needs_review`. The one exception is a retry, which MAY return a request to `approved` only if it failed while already in `approved`. No other path SHALL exist, so that no model output or message content can cause an approval.

#### Scenario: System cannot approve a flagged request
- **WHEN** the system tries to move a request from `needs_review` to `approved`
- **THEN** the transition is rejected

#### Scenario: Staff approves a flagged request
- **WHEN** staff moves a request from `needs_review` to `approved`
- **THEN** the request's state becomes `approved`

#### Scenario: Retry after a failed send returns to approved
- **WHEN** a request that failed while in `approved` is retried
- **THEN** its state becomes `approved` again

#### Scenario: Retry cannot reach approved from an earlier step
- **WHEN** a request that failed in `drafting` is moved from `failed` to `approved` by anyone
- **THEN** the transition is rejected

#### Scenario: Approval cannot skip the checks
- **WHEN** anyone tries to move a request from `drafting` or `checking` directly to `approved`
- **THEN** the transition is rejected

### Requirement: Failures record the failed step and the error
Only the `system` SHALL move a request to `failed`, and only from `extracting`, `checking`, `resolving`, `drafting`, `approved`, or `rejected`. It SHALL record the state it failed in and an error message. A retry, by `system` or `staff`, SHALL return the request to exactly that state and clear the failure. Staff MAY instead move it to `rejected`.

#### Scenario: Failure is recorded
- **WHEN** a request in `extracting` moves to `failed` with error "model timeout"
- **THEN** its failed step is `extracting` and its last error is "model timeout"

#### Scenario: Retry returns to the failed step
- **WHEN** a request that failed in `extracting` is retried
- **THEN** its state becomes `extracting` and its failed step and last error are cleared

#### Scenario: Retry to a different step is rejected
- **WHEN** a request that failed in `extracting` is moved from `failed` to `drafting`
- **THEN** the transition is rejected

#### Scenario: Staff gives up on a failed request
- **WHEN** staff moves a failed request to `rejected`
- **THEN** the request's state becomes `rejected`

### Requirement: Every transition is logged
Every successful transition SHALL append one entry to the request's transition log with the from-state, to-state, actor, an optional reason, and a timestamp. A rejected transition SHALL NOT add an entry. The log entry and the state change SHALL be saved together or not at all.

#### Scenario: Successful transition adds a log entry
- **WHEN** staff moves a request from `needs_review` to `rejected` with reason "vaccines expired"
- **THEN** the log gains one entry: `needs_review` → `rejected`, actor `staff`, reason "vaccines expired"

#### Scenario: Rejected transition adds nothing
- **WHEN** an illegal transition is attempted
- **THEN** the request's transition log is unchanged

### Requirement: Concurrent updates do not overwrite each other
If two updates are based on the same version of a booking request, only the first SHALL be saved. The second SHALL be rejected with a conflict error, and it SHALL NOT write a transition log entry.

#### Scenario: Stale update is rejected
- **WHEN** two sessions both load a request in `needs_review`, one moves it to `approved`, and the other then tries to move it to `rejected`
- **THEN** the second update fails with a conflict error
- **AND** the request stays `approved` with exactly one new log entry

### Requirement: Staff decisions are recorded as approvals
Each staff decision on a request SHALL be stored as an approval record with the action (`approve`, `edit_and_approve`, or `reject`), the staff member's name, a timestamp, and any reason or edited reply text. A `reject` action SHALL include a reason.

#### Scenario: Reject without a reason is rejected
- **WHEN** a `reject` approval record is stored with no reason
- **THEN** the database rejects the record
