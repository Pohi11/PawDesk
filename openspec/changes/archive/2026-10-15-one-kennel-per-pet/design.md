# Design

## Context

- **Kennel overlap** is already guarded twice (design D5 of the domain model; stay dates per decision record [0005](../../../../docs/decisions/0005-stay-date-semantics.md)): `find_kennel` skips kennels with a reservation sharing a night, and the exclusion constraint `ex_reservations_no_overlapping_stays` refuses a second reservation for the same kennel and night. Nothing looks at the pet.
- **A confirmed boarding request reserves at send time** (`_reserve_if_confirmed`), after searching for a kennel again.
- **The demo database is shared.** Every run of the clean sample is approved and reserves a medium kennel for Mar 24–27, and there are three. Generated boarding requests fall on Mar 8 to Apr 12 of the same demo year.

## Goals / Non-Goals

**Goals:** one pet never holds two kennels on one night; a duplicate request goes to a person; the fixed samples end the same way however often they run.

**Non-Goals:** merging or extending an existing stay; releasing kennels for generated requests; a general demo reset.

## Decisions

### D1. Pet overlap is a constraint plus an advisory check, like kennel overlap
- **The constraint** `ex_reservations_one_kennel_per_pet` (pet `=`, nights `&&`, half-open `[)`) is the guarantee, because a check-then-insert can race. It reuses the same range shape as the kennel constraint, so "shares a night" means one thing everywhere.
- **The check** (`find_pet_stay` in `app/capacity.py`) runs first in the capacity step, so a duplicate is caught at routing with a readable reason instead of failing at send time.
- **At send time** the pet is checked again before the kennel search, and an insert refused by either constraint fails the step, as the kennel race does today.

### D2. Already booked goes to a person, not to the resolver
- **The capacity status is `already_booked`,** separate from `none_free`. Other dates or a larger kennel don't help when the pet is already staying; the likely cause is a duplicate, or a change to an existing stay, which staff should handle.
- **The resolver's scope** therefore lists it among the problems that need a person, so the resolution is `not_attempted` and no model is called (existing requirement "Code decides whether the resolver runs").
- **Verified options** also fail if the pet already has a kennel on any of their nights, so the resolver can't offer dates that overlap the pet's other stay.

### D3. The migration keeps each pet's earliest reservation
- **The constraint can't be added while overlaps exist,** and the local and hosted demo databases have them. The migration deletes any reservation that shares a night with an earlier reservation (by creation time, then id) for the same pet, then adds the constraint.
- **All data is synthetic,** so deleting the later duplicates loses nothing real. Downgrade drops the constraint and does not restore the rows.

### D4. A boarding sample releases what earlier requests hold in its way
- **Released:** reservations with a `booking_request_id`, in a kennel of the sample pet's size class, sharing a night with the sample's stay. That covers the sample's own earlier runs and generated requests that took the same kennels.
- **Kept:** seeded reservations (no request), other size classes, other nights. The seed's full medium weekend is relative to today and unaffected.
- **Why on submit, not a reset button:** the sample's stated outcome ("the checks pass it") should hold on every run without a visitor knowing to reset first. The sample knows its pet and dates (`Sample.pet`, `start_date`, `end_date`), so the release is exact.
- **Edited messages:** the release uses the sample's stay, not dates read from an edited message.
- **Trade-off:** an earlier request stays `sent` with a confirmation, but its kennel is gone. For a demo this is acceptable; it is limited to fixed samples, never to normal intake.

## Risks / Trade-offs

- [Two visitors run samples at once on the hosted demo] → One run may release the other's reservation before it is sent; the second then reserves a kennel normally. The constraints still prevent any double booking.
- [A real customer extends a stay with a new request] → It goes to a person (D2). Handling extensions automatically is out of scope.
