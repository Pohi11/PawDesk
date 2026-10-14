# booking-reply Specification

## Purpose
Drafts the reply to the pet parent from structured facts, checks deterministically that it promises nothing the checks didn't confirm, and decides whether it can go out automatically or must wait for a person.

## Requirements

### Requirement: The reply is drafted from structured facts only
The reply agent SHALL receive only values produced by code or kept on file: the owner's and pet's names on file, the facility's name, the service, the requested dates, the situation (`confirmed`, `alternatives`, or `under_review`), and the verified options. It SHALL NOT receive the customer's message, notes, or certificate text. Its output SHALL be validated as a subject of at most 120 characters and a body of at most 1500 characters.

#### Scenario: Confirmed request
- **WHEN** a request passed every check without resolving
- **THEN** the reply is drafted with situation `confirmed`, and no request sent to the model contains the customer's message text

#### Scenario: Only verified options are offered
- **WHEN** the resolver proposed one verified and one unverified option
- **THEN** the reply facts contain only the verified option

#### Scenario: Nothing to offer
- **WHEN** the resolution was escalated or not attempted, or no option was verified
- **THEN** the reply is drafted with situation `under_review`

### Requirement: Replies never promise what the checks didn't confirm
Every draft SHALL be checked by code before it can be sent. The check SHALL report:
- each date in the body that is neither a requested date nor a date of a verified option;
- commitment words ("booked", "confirmed", "reserved", "approved") when the situation is not `confirmed`;
- any amount of money.

#### Scenario: Unconfirmed date
- **WHEN** a confirmed reply for March 10–13 also mentions March 15
- **THEN** the check reports March 15 as an unconfirmed date

#### Scenario: Commitment without confirmation
- **WHEN** a reply with situation `alternatives` says the stay is booked
- **THEN** the check reports a commitment word

#### Scenario: Price
- **WHEN** a reply mentions "$45 per night"
- **THEN** the check reports a price

#### Scenario: Clean reply
- **WHEN** a confirmed reply mentions only the requested dates and says the stay is confirmed
- **THEN** the check reports nothing

### Requirement: Flagged replies wait for a person
After drafting, a request SHALL move to `needs_review` when it came through `resolving` or its draft failed the promise check, and SHALL move to `ready` otherwise. The saved reply result SHALL list every flag reason.

#### Scenario: Clean request is ready
- **WHEN** a confirmed request's draft passes the promise check
- **THEN** the request moves to `ready` with no flag reasons

#### Scenario: Resolved request waits
- **WHEN** a request came through `resolving`
- **THEN** it moves to `needs_review` with a reason naming the resolution

#### Scenario: Failed promise check waits
- **WHEN** a confirmed request's draft mentions a price
- **THEN** it moves to `needs_review` with the promise check's finding as a reason
