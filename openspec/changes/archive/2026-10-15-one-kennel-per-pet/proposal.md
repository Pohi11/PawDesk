# Proposal

## Why

Running the clean boarding sample several times books Biscuit into every medium kennel for the same nights (M1, M2, M3, all Mar 24–27). Two problems show:

- **Nothing stops one pet from holding two kennels on the same night.** A repeated or duplicate request is approved and reserves another kennel, as if a second dog were coming.
- **The demo samples stop showing what they promise.** Once earlier runs fill the medium kennels, the clean sample is routed to a person with "no free medium kennel for the stay". Generated requests (stays 5 to 40 days after the demo day) fill the same kennels over time on the hosted demo.

## What Changes

- **A pet holds at most one kennel per night.** The database refuses a reservation that shares a night with another reservation for the same pet, as it already does for the same kennel.
- **The checks notice a pet already booked for the stay.** For boarding, the capacity check first looks for a reservation of the same pet that shares a night with the stay. If it finds one, no kennel is searched, and the request goes to a person with the reason "capacity: Biscuit already has a kennel for these nights".
- **Running a boarding sample frees its stay.** Before a fixed sample's request is stored, reservations made by earlier requests in the sample pet's size class that share a night with the sample's stay are released. Seeded reservations are kept.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `kennel-capacity`: a pet holds at most one kennel per night.
- `booking-orchestration`: a pet already booked for the stay is not booked again.
- `observability-api`: running a boarding sample frees its stay.

## Impact

- **Database:** a migration removes existing same-pet overlaps (keeping each pet's earliest reservation) and adds an exclusion constraint on `reservations` (pet, nights).
- **Backend:** `app/capacity.py` (pet overlap lookup), `app/orchestrator.py` (capacity check, send-time recheck, routing reason), `app/resolver.py` (an already-booked pet needs a person), `app/demo.py` (release before a sample is stored), `app/models/domain.py`.
- **Frontend:** `lib/step-summary.ts` (the capacity step's sentence for an already-booked pet).
- **Tests:** capacity, orchestration, resolver scope, and demo API tests; a step-summary unit test.
