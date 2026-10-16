# Tasks

## 1. One kennel per pet

- [ ] 1.1 Add the pet overlap constraint to `Reservation` and a migration that removes later same-pet overlaps first. Verify with capacity tests for the refused and back-to-back inserts.
- [ ] 1.2 Add `find_pet_stay` to `app/capacity.py`. Verify with a lookup test.

## 2. Checks, routing, sending

- [ ] 2.1 Report `already_booked` from the capacity check before any kennel search, add the routing reason, and send it to a person in the resolver's scope; fail verified options that overlap the pet's other stay. Verify with orchestration and resolver tests.
- [ ] 2.2 Check the pet again at send time, and fail the step when either constraint refuses the insert. Verify with a send-time test.
- [ ] 2.3 Show the already-booked sentence on the capacity step. Verify with a step-summary unit test.

## 3. Demo samples

- [ ] 3.1 Release reservations in a boarding sample's way before storing it. Verify with demo API tests for the three scenarios.

## 4. Integration

- [ ] 4.1 Migrate the local database, run the clean sample twice live and check both are sent, then run every suite and the coverage check, and regenerate the walkthrough.
