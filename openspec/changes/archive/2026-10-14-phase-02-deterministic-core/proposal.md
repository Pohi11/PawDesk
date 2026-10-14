# Proposal

## Why

The two questions that decide whether a booking can be accepted, "are this pet's vaccines valid for the whole stay?" and "is a kennel of the right size free every night?", have exact answers. They must be answered by tested code, not by a model. Later LLM steps only supply inputs to these checks (dates, vaccine records). If the checks aren't trusted first, a wrong reply could come from either the model or the rules, with no way to tell which.

## What Changes

- Add a pure compliance check that takes the required vaccines, a pet's vaccine records, and the stay dates. It returns a status for each vaccine (`ok`, `missing`, `expired`, `expires_during_stay`, `not_yet_given`, `unknown_expiry`) and an overall outcome (`compliant`, `not_compliant`, `needs_review`).
- Fix the date semantics used everywhere:
  - Stay dates are calendar dates in the facility's time zone.
  - A pet is on site every date from check-in through checkout, inclusive.
  - A vaccine's expiry date is the last day it is valid.
- Add a loader that reads a facility's required vaccines for a service and species, plus a pet's vaccine records, from the database.
- Add a kennel search that returns a free kennel of an exact size class for every night of a stay, or nothing. When several qualify, the choice is deterministic.
- Add conversion from an instant in time to a facility's local calendar date.

## Capabilities

### New Capabilities
- `vaccine-compliance`: Whether a pet's vaccine records satisfy a facility's rules for a service over a given stay, with a per-vaccine explanation and an outcome that separates "fails" from "a person must check."
- `kennel-capacity`: Finding a kennel of a given size class that is free for every night of a stay.

### Modified Capabilities
- `booking-domain`: adds a requirement for converting an instant to a facility's local calendar date (the existing time-zone requirement stays unchanged).

## Impact

- **Backend:** new modules `app/compliance.py` (pure check plus a database loader), `app/capacity.py` (kennel search), and a date helper. No schema changes and no new dependencies.
- **Downstream:** the vaccine-record extraction step (Phase 5) has to produce records in the same shape and with the same expiry meaning. The resolver (Phase 7) builds alternative offers on top of the kennel search.
- **Out of scope:** reserving a kennel (writing a reservation), offering a larger kennel as a substitute, minimum waiting periods after vaccination (for example, Bordetella given at least 7 days before arrival), and partial-day pricing.
