# Design

## Context

- **Services** (`app/intake.py`, `app/orchestrator.py`): boarding needs an end date after its start; daycare and grooming start and end on the same day. Only boarding searches for a kennel and reserves one when the reply goes out.
- **Vaccine rules** are set per facility, service, and species (spec `booking-domain`). The seeded facility requires, for dogs, Rabies, DHPP, and Bordetella for boarding, those plus canine influenza for daycare, and Rabies for grooming; cats need Rabies and FVRCP for boarding and daycare, and Rabies for grooming.
- **Coverage** (spec `vaccine-compliance`): a pet is on site from the start date through the end date. A record covers the stay if it was given on or before the start and expires on or after the end. Any one covering record is enough. A record without an expiry goes to a person.
- **Size class** (`SIZE_CLASS_SQL`): cats get cat kennels; dogs are small under 20 lb, medium under 50, large under 90, extra large from 90. The search looks only at the pet's own size, for a kennel with no booked night in the stay.
- **Dates** (`BOOKING_HORIZON_DAYS`): a stay can start today or up to 365 days ahead.

## Goals / Non-Goals

**Goals:** a visitor can say which service needs what, and why a given request passed or failed, before reading about the agents.

**Non-Goals:** changing any rule; an API for the rules.

## Decisions

### D1. A comparison table for the services
- **Three services by four questions** (visit, kennel, dogs need, cats need) is a grid, so it's a table with one row per service, like the agents table. Below 1024 px each service stacks with its four answers, each labeled.

### D2. One date strip for coverage
- **"Covers the stay" is the rule visitors misread most**: the shot has to last through pickup day, not only drop-off. A strip of the days March 23 to 28, with the stay marked and two vaccine bars under it (one lasting past pickup, one ending on the 26th), shows it faster than a sentence.
- **It reuses the worked example's stay** (Biscuit, March 24 to 27), so the page tells one story.
- **Colors keep their dashboard meaning:** green for a check that passed, red for one that failed.

### D3. The rule data is shared and tested
- **Options considered:**
  - hand-write the lists in the page (they drift when the seed changes);
  - add an API endpoint for the rules (more surface for a static explanation);
  - keep the data in a JSON file the page imports, and test it against the backend.
- **Decision:** `frontend/content/booking-rules.json`, checked by a backend test against `RULES` in the seed script, the thresholds parsed from `SIZE_CLASS_SQL`, and `BOOKING_HORIZON_DAYS`. This follows `docs/style/copy-rules.json`, which both sides already read.
- **Prose stays in the page;** only values with a right answer live in the file.

### D4. Placement
- **Before the agents,** so "code checks the vaccines" in the agents table refers to rules the visitor has already read.

## Risks / Trade-offs

- [The rules are the demo facility's, and a real facility sets its own] → The section says so in its first sentence.
- [The date strip is hand-drawn from fixed dates] → They are the clean sample's dates, which the end-to-end tests already pin.
