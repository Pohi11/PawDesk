"""Vaccine compliance (spec: vaccine-compliance, design D2–D5, decision record 0005).

`check()` is pure: plain values in, plain values out, no I/O. Records from the database
and records extracted from a certificate image both arrive as `VaccineEvidence`.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from app.enums import Vaccine


class VaccineStatus(StrEnum):
    OK = "ok"
    MISSING = "missing"
    UNKNOWN_EXPIRY = "unknown_expiry"
    EXPIRES_DURING_STAY = "expires_during_stay"
    NOT_YET_GIVEN = "not_yet_given"
    EXPIRED = "expired"


class Outcome(StrEnum):
    COMPLIANT = "compliant"
    NOT_COMPLIANT = "not_compliant"
    NEEDS_REVIEW = "needs_review"


@dataclass(frozen=True)
class VaccineEvidence:
    vaccine: Vaccine
    administered_on: date
    expires_on: date | None  # last valid day, inclusive; None = not stated


@dataclass(frozen=True)
class VaccineCheck:
    vaccine: Vaccine
    status: VaccineStatus


@dataclass(frozen=True)
class ComplianceResult:
    outcome: Outcome
    checks: tuple[VaccineCheck, ...]  # one per required vaccine, sorted by vaccine


FAILURES = frozenset(
    {
        VaccineStatus.MISSING,
        VaccineStatus.EXPIRED,
        VaccineStatus.EXPIRES_DURING_STAY,
        VaccineStatus.NOT_YET_GIVEN,
    }
)


def vaccine_status(records: list[VaccineEvidence], start: date, end: date) -> VaccineStatus:
    """Status of one vaccine, given only that vaccine's records.

    The pet is on site from `start` through `end` inclusive (decision record 0005), so a
    record covers the stay when it was given by `start` and is valid through `end`.
    Uncovered vaccines take the first matching explanation, in spec order (design D3).
    """
    if not records:
        return VaccineStatus.MISSING

    given_by_start = [r for r in records if r.administered_on <= start]
    if any(r.expires_on is not None and r.expires_on >= end for r in given_by_start):
        return VaccineStatus.OK
    if any(r.expires_on is None for r in given_by_start):
        return VaccineStatus.UNKNOWN_EXPIRY
    # Covering records already returned above, so any expiry still >= start is < end.
    if any(r.expires_on >= start for r in given_by_start):
        return VaccineStatus.EXPIRES_DURING_STAY
    if any(r.administered_on > start for r in records):
        return VaccineStatus.NOT_YET_GIVEN
    return VaccineStatus.EXPIRED


def check(
    required: Iterable[Vaccine], records: Iterable[VaccineEvidence], start: date, end: date
) -> ComplianceResult:
    if end < start:
        raise ValueError(f"stay end {end} is before start {start}")

    by_vaccine: dict[Vaccine, list[VaccineEvidence]] = {}
    for record in records:
        by_vaccine.setdefault(record.vaccine, []).append(record)

    checks = tuple(
        VaccineCheck(vaccine, vaccine_status(by_vaccine.get(vaccine, []), start, end))
        for vaccine in sorted(set(required))
    )
    statuses = {c.status for c in checks}
    if statuses & FAILURES:
        outcome = Outcome.NOT_COMPLIANT
    elif VaccineStatus.UNKNOWN_EXPIRY in statuses:
        outcome = Outcome.NEEDS_REVIEW
    else:
        outcome = Outcome.COMPLIANT
    return ComplianceResult(outcome=outcome, checks=checks)
