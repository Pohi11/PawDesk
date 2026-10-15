# Proposal

## Why

The home page says code checks the vaccines and finds a kennel, but never says what those checks are. A visitor can't tell that grooming is a same-day visit with no kennel, that boarding needs at least one night and a kennel of the pet's size, or which vaccines each service needs. Without the rules, the agents and steps sections describe a system whose logic stays hidden.

## What Changes

- **A new section, "Booking rules", between the Try panel and "The agents".** It covers:
  - each service (boarding, daycare, grooming): how long a visit lasts, whether it needs a kennel, and which vaccines dogs and cats need;
  - when a vaccine counts for a stay, with a small date strip showing one shot that covers a stay and one that expires during it;
  - how a dog's weight sets its kennel size, and when a kennel counts as free;
  - which dates a request can ask for;
  - what happens when a rule isn't met.
- **The rule data lives in `frontend/content/booking-rules.json`.** The page reads it, and a backend test checks it against the seeded facility's vaccine rules, the size class thresholds, and the booking horizon.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `run-dashboard`: the home page explains the booking rules.

## Impact

- **Frontend:** `app/page.tsx`, a new `content/booking-rules.json`.
- **Backend:** a test only (`tests/test_home_page_rules.py`).
- **Tests:** the backend test for the rule data, and the home page end-to-end test for the section.
