# Design

## Context

The schema from the domain-model change already stores everything these checks need:
- `vaccine_rules` (facility, service, species, vaccine)
- `vaccine_records` (pet, vaccine, administered_on, nullable expires_on)
- `kennels` (facility, name, size_class)
- `reservations`, whose half-open `[start, end)` exclusion constraint already defines "overlapping nights"

`pets.size_class` is computed by Postgres. The seed data covers an expired vaccine, one that expires mid-stay, one with an unknown expiry, and a weekend where every medium kennel is taken. See `proposal.md` for motivation and `specs/` for the required behavior.

## Goals / Non-Goals

**Goals:**
- The compliance decision is a pure function. Its inputs are plain values, not ORM objects, so it runs in microseconds and can be tested at every date boundary without a database.
- Records loaded from the database and records extracted from a certificate image (later) feed the same function in the same shape.
- The kennel search asks the database the same overlap question the exclusion constraint enforces.

**Non-Goals:**
- Writing reservations.
- Offering larger kennels or alternative dates (the resolver's job).
- Waiting periods after vaccination.
- Caching.

## Decisions

### D1. Date semantics are fixed once, for every component
Stay dates are calendar `date`s in the facility's time zone:
- A pet is on site from the start date through the end date, inclusive. The end date is checkout day.
- A day service has start = end.
- Kennel nights are `[start, end)`.
- `expires_on` is the last valid day, inclusive.

Converting an instant to a date happens once, at the boundary, using the facility's time zone. This affects the records-extraction and reply steps too, so it is recorded as [decision record 0005](../../../../docs/decisions/0005-stay-date-semantics.md).
- *Alternatives:* treating `expires_on` as the first invalid day (the opposite of how certificates are read), or storing stays as timestamps (that adds check-in hours and time-zone arithmetic to every comparison, for no benefit at day granularity).

### D2. Plain value types at the boundary of the pure check
`app/compliance.py` defines frozen dataclasses:
- `VaccineEvidence(vaccine, administered_on, expires_on)` (input)
- `VaccineCheck(vaccine, status)` (output)
- `ComplianceResult(outcome, checks)` (output)

`check(required, records, start, end)` takes a set of required `Vaccine`s and an iterable of `VaccineEvidence`.
- *Why not ORM objects:* the function would then need a session to exist, and the extraction step (which produces records that aren't stored yet) couldn't call it.
- *Why not Pydantic:* these values are never parsed from untrusted input here. Pydantic stays at the LLM boundary, where validation is the point.

### D3. Status precedence is an ordered rule list
For an uncovered vaccine, the status is the first match in a fixed order: missing → unknown_expiry → expires_during_stay → not_yet_given → expired (see the spec). The order is chosen for usefulness to staff and the pet parent. An unknown expiry is a question to ask, not a failure, so it outranks older expired records. A record expiring mid-stay outranks an older expired record, because it's the one the owner can renew.
- *Alternative:* reporting every record's problem. That's noisier, and the reply step would have to pick one anyway.

### D4. Outcome is derived only from the statuses
Hard failures produce `not_compliant`. Otherwise `unknown_expiry` produces `needs_review`. Otherwise the outcome is `compliant`. `needs_review` feeds the human-approval path later. It's how "don't guess" becomes a workflow state instead of a silent assumption.

### D5. Thin async loader, separate from the pure check
`load_requirements(session, facility_id, service, species)` and `load_evidence(session, pet_id)` return the plain values. `check_pet(session, pet, facility_id, service, start, end)` composes them. Only the loader touches the database.

### D6. Kennel search: one query with `NOT EXISTS` and `daterange` overlap
`find_kennel(session, facility_id, size_class, start, end)`:

```sql
SELECT k.* FROM kennels k
WHERE k.facility_id = :f AND k.size_class = :size
  AND NOT EXISTS (
    SELECT 1 FROM reservations r
    WHERE r.kennel_id = k.id
      AND daterange(r.start_date, r.end_date, '[)') && daterange(:start, :end, '[)'))
ORDER BY k.name LIMIT 1
```

- **Same overlap rule:** the operator and range bounds match the exclusion constraint exactly, so the search and the constraint can't disagree about what overlapping means.
- **Indexes:** the exclusion constraint's GiST index on `(kennel_id, daterange)` also serves the `NOT EXISTS` lookup.
- **The result is advisory:** another transaction can take the kennel between the search and the insert. The constraint remains the real guarantee, and whatever reserves the kennel later must handle the conflict error.
- *Alternatives:* load all reservations and filter in Python (slower, and it duplicates the overlap rule); `SELECT … FOR UPDATE` locking (premature, because nothing reserves in this change).

### D7. Local date helper
`facility_date(timezone: str, instant: datetime) -> date` raises `ValueError` for a naive datetime. Otherwise it returns `instant.astimezone(ZoneInfo(timezone)).date()`.

## Risks / Trade-offs

- [Choosing exact size class only means a medium dog is refused even when a large kennel is free] → This is intentional. Offering an upgrade is a business decision and belongs to the resolver (Phase 7), not to a yes/no capacity check.
- [The precedence order is a judgment call] → It's written into the spec with scenarios, so changing it is a spec change, not a silent edit.
- [The pure check trusts its inputs (for example, `administered_on` after `expires_on`)] → The database already rejects such records. Extracted records are validated at the LLM boundary before they reach the check.
- [Search-then-reserve race] → See D6. The exclusion constraint makes the race safe, and the conflict surfaces as an error to handle.
