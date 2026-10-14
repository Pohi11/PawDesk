# 0005 — Stay dates are facility-local calendar dates; expiry is inclusive

- **Date:** 2026-10-14
- **Status:** Accepted

## Context

Several components reason about the same dates: vaccine compliance, kennel capacity, extracting records from certificate images, the resolver's alternative offers, and the reply sent to pet parents. If any two of them read a date differently, the result is an off-by-one decision. Examples: a vaccine treated as valid on the day it lapses, or a night counted twice. Ambiguity hides in four places:

- Is a printed expiry date the last valid day or the first invalid day?
- Is the pet on site on checkout day?
- Which time zone turns "now" into "today"?
- Are kennel stays measured in days or in nights?

## Options considered

1. **Timestamps everywhere** (check-in and checkout times, expiry at midnight in some zone). Precise, but every comparison needs time-zone arithmetic, check-in hours vary by facility, and certificates only carry dates.
2. **Calendar dates in UTC.** Simple, but a late-evening request in Chicago lands on the next UTC day.
3. **Calendar dates in the facility's time zone, with fixed meanings for each boundary.**

## Decision

Option 3.

- **Stay dates** are `date` values in the facility's IANA time zone (`facilities.timezone`).
- **Days on site:** a pet is on site every date from the start date through the end date, **inclusive**. The end date is checkout day. A day service (daycare, grooming) has start = end.
- **Kennel nights** run from the start date up to, but **not including**, the end date: `[start, end)`. That matches the reservation exclusion constraint, so back-to-back stays don't conflict.
- **Vaccine expiry:** `expires_on` is the **last valid day**, inclusive. A record covers a stay when `administered_on <= start` and `expires_on >= end`.
- **Converting instants to dates:** happens once, at the boundary, with `facility_date(timezone, instant)`. Naive datetimes are rejected rather than guessed.

## Consequences

- **Good:** Compliance, capacity, extraction, and replies share one set of meanings. The boundary cases (expires on checkout day, back-to-back stays) are pinned by tests.
- **Good:** Days on site and kennel nights are two views of the same stay. A Mar 6–9 stay is 4 days on site and 3 kennel nights.
- **Cost:** Every extraction prompt and reply template has to use these meanings. For example, a certificate's "expires 03/09/2027" is stored as `2027-03-09`, and a reply says "valid through" rather than "until".
- **Cost:** Facilities that check vaccines against arrival only (not checkout) would need a separate rule. That is out of scope for now.
