"""The resolver: a bounded agent that proposes alternatives for a blocked booking request
(spec: booking-resolution; decision record 0010).

Fenced in on every side:
- code decides whether it runs at all (`resolution_scope`);
- its prompt holds only values code produced, never customer text;
- its tools only read, and the request's pet, facility, and service are bound in code;
- the loop stops on a proposal, a repeated call, a missing tool call, or a step limit;
- every proposed option is re-checked by code, and nothing it returns can approve.
"""

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Any

from app.compliance import VaccineStatus

# Vaccine problems an alternative can address: other dates, or an updated record. An
# unknown expiry needs a person to read the record, so it is not on this list.
FIXABLE_VACCINE_STATUSES = frozenset(
    {
        VaccineStatus.MISSING,
        VaccineStatus.EXPIRED,
        VaccineStatus.EXPIRES_DURING_STAY,
        VaccineStatus.NOT_YET_GIVEN,
    }
)


class ResolutionOutcome(StrEnum):
    PROPOSED = "proposed"
    ESCALATED = "escalated"  # the agent ran and stopped without a valid proposal
    NOT_ATTEMPTED = "not_attempted"  # outside what alternatives can fix: a person decides


@dataclass(frozen=True)
class Scope:
    """What the checks found, sorted into what the agent may work on and what it may not."""

    needs_person: list[str] = field(default_factory=list)
    vaccines: list[dict[str, str]] = field(default_factory=list)  # fixable: {vaccine, status}
    capacity_full: bool = False

    @property
    def eligible(self) -> bool:
        return not self.needs_person and (bool(self.vaccines) or self.capacity_full)


def resolution_scope(intake: dict, records: dict, checks: dict) -> Scope:
    """Pure: the saved step results decide whether the agent runs (design D2)."""
    needs_person = [f"intake: {issue}" for issue in intake["issues"]]
    needs_person += [f"records: {issue}" for issue in records["issues"]]
    if checks["not_checked"]:
        needs_person.append(checks["not_checked"])
    if checks["pet"]["mismatch"]:
        needs_person.append(checks["pet"]["mismatch"])

    vaccines = []
    for c in (checks["compliance"] or {}).get("checks", []):
        if c["status"] in FIXABLE_VACCINE_STATUSES:
            vaccines.append({"vaccine": c["vaccine"], "status": c["status"]})
        elif c["status"] != VaccineStatus.OK:
            needs_person.append(f"vaccine {c['vaccine']}: {c['status']}")

    capacity = checks["capacity"] or {}
    if capacity.get("status") == "not_checked":
        needs_person.append("capacity: not checked")

    return Scope(needs_person, vaccines, capacity.get("status") == "none_free")


@dataclass(frozen=True)
class RequestFacts:
    """The structured facts the prompt is built from. Deliberately has no field that could
    carry customer text: no message, no notes, not even the pet's name."""

    service: str
    species: str
    size_class: str
    start: date
    end: date
    today: date


def prompt_context(facts: RequestFacts, scope: Scope) -> dict[str, Any]:
    return {
        "today": facts.today.isoformat(),
        "service": facts.service,
        "species": facts.species,
        "size_class": facts.size_class,
        "requested_stay": {
            "start_date": facts.start.isoformat(),
            "end_date": facts.end.isoformat(),
            "days_on_site": (facts.end - facts.start).days + 1,
        },
        "problems": {
            "vaccines": scope.vaccines,
            "capacity": (
                "no free kennel of this size for the requested nights"
                if scope.capacity_full
                else None
            ),
        },
    }


def request_facts(intake: dict, species: str, size_class: str, today: date) -> RequestFacts:
    """Only the typed fields of the saved intent are read; its free-text fields (notes,
    ambiguities, the pet's name as written) are never touched."""
    intent = intake["intent"]
    return RequestFacts(
        service=intent["service"],
        species=species,
        size_class=size_class,
        start=date.fromisoformat(intent["start_date"]),
        end=date.fromisoformat(intent["end_date"]),
        today=today,
    )
