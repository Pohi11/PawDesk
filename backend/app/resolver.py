"""The resolver: a bounded agent that proposes alternatives for a blocked booking request
(spec: booking-resolution; decision record 0010).

Fenced in on every side:
- code decides whether it runs at all (`resolution_scope`);
- its prompt holds only values code produced, never customer text;
- its tools only read, and the request's pet, facility, and service are bound in code;
- the loop stops on a proposal, a repeated call, a missing tool call, or a step limit;
- every proposed option is re-checked by code, and nothing it returns can approve.
"""

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.capacity import find_kennel, free_kennel_counts
from app.compliance import VaccineEvidence, VaccineStatus, check
from app.enums import Service, SizeClass, Species, Vaccine
from app.intake import BOOKING_HORIZON_DAYS
from app.structured import strict_json_schema

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


# --- Tools (design D4) -------------------------------------------------------------------
#
# Each tool only reads. The request's pet, facility, service, and dates are bound in
# `ToolContext` by code; the model can only choose a search range, dates, or a size class.

MAX_SHIFT_DAYS = 14
MAX_WINDOWS = 5
DOG_SIZES = (SizeClass.SMALL, SizeClass.MEDIUM, SizeClass.LARGE, SizeClass.XLARGE)


class ToolError(Exception):
    """A problem the model can fix by calling differently. Returned to it as data."""


@dataclass(frozen=True)
class ToolContext:
    facility_id: uuid.UUID
    species: Species
    size_class: SizeClass
    service: Service
    start: date
    end: date
    today: date
    required: frozenset[Vaccine]
    evidence: tuple[VaccineEvidence, ...]  # records on file plus records from the certificate


class _Args(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FindAlternativeDates(_Args):
    """Find nearby stays with the same number of days, shifted earlier or later, where a
    kennel of the pet's size is free (boarding). Each window says whether the pet's
    vaccines cover it."""

    max_shift_days: int = Field(
        ge=1, le=MAX_SHIFT_DAYS, description="Search up to this many days earlier or later (1-14)."
    )


class _Window(_Args):
    start_date: date = Field(description="First day on site, YYYY-MM-DD.")
    end_date: date = Field(description="Last day on site (checkout day), YYYY-MM-DD.")

    @model_validator(mode="after")
    def _ordered(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date is before start_date")
        return self


class ListMissingVaccines(_Window):
    """List the required vaccines that would not cover a stay on these dates, with why and
    the last known expiry."""


class CheckKennelSizes(_Window):
    """Count free kennels of each size class for every night of a stay on these dates."""

    @model_validator(mode="after")
    def _has_a_night(self):
        if self.end_date == self.start_date:
            raise ValueError("a kennel stay needs at least one night")
        return self


class AlternativeDatesOption(_Args):
    kind: Literal["alternative_dates"]
    start_date: date = Field(description="YYYY-MM-DD")
    end_date: date = Field(description="YYYY-MM-DD")


class LargerKennelOption(_Args):
    kind: Literal["larger_kennel"]
    size_class: SizeClass


class VaccineUpdateOption(_Args):
    kind: Literal["vaccine_update"]
    vaccines: list[Vaccine] = Field(min_length=1, max_length=7)


# A plain union (no discriminator), so the schema is a simple anyOf; each option's literal
# `kind` and extra="forbid" still let exactly one model match.
Option = AlternativeDatesOption | LargerKennelOption | VaccineUpdateOption
Summary = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=400)]


class ProposeOffer(_Args):
    """Finish by proposing one to three options for staff to review. This cannot approve or
    book anything."""

    options: list[Option] = Field(min_length=1, max_length=3)
    summary: Summary = Field(description="One or two sentences for staff.")


def tool_schema(name: str, args: type[BaseModel]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": " ".join((args.__doc__ or "").split()),
            "parameters": strict_json_schema(args),
        },
    }


def _check_window(ctx: ToolContext, start: date, end: date) -> None:
    if start < ctx.today:
        raise ToolError(f"start_date {start} is before today ({ctx.today})")
    if start > ctx.today + timedelta(days=BOOKING_HORIZON_DAYS):
        raise ToolError(f"start_date {start} is more than {BOOKING_HORIZON_DAYS} days away")


def _failing(ctx: ToolContext, start: date, end: date) -> list[dict[str, str]]:
    result = check(ctx.required, ctx.evidence, start, end)
    return [
        {"vaccine": str(c.vaccine), "status": str(c.status)}
        for c in result.checks
        if c.status != VaccineStatus.OK
    ]


async def find_alternative_dates(
    session: AsyncSession, ctx: ToolContext, args: FindAlternativeDates
) -> dict[str, Any]:
    windows = []
    # Nearest first; on a tie, earlier first: -1, +1, -2, +2, ...
    for shift in (sign * d for d in range(1, args.max_shift_days + 1) for sign in (-1, 1)):
        start, end = ctx.start + timedelta(days=shift), ctx.end + timedelta(days=shift)
        if start < ctx.today or start > ctx.today + timedelta(days=BOOKING_HORIZON_DAYS):
            continue
        kennel = None
        if ctx.service == Service.BOARDING:
            kennel = await find_kennel(session, ctx.facility_id, ctx.size_class, start, end)
            if kennel is None:
                continue
        failing = _failing(ctx, start, end)
        windows.append(
            {
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "shift_days": shift,
                "kennel": kennel.name if kennel else None,
                "vaccines_cover_stay": not failing,
                "failing_vaccines": failing,
            }
        )
        if len(windows) == MAX_WINDOWS:
            break
    result: dict[str, Any] = {"windows": windows}
    if not windows:
        result["note"] = f"no window within {args.max_shift_days} days has a free kennel"
    return result


async def list_missing_vaccines(
    session: AsyncSession, ctx: ToolContext, args: ListMissingVaccines
) -> dict[str, Any]:
    _check_window(ctx, args.start_date, args.end_date)
    missing = []
    for failing in _failing(ctx, args.start_date, args.end_date):
        records = [e for e in ctx.evidence if e.vaccine == failing["vaccine"]]
        given = max((e.administered_on for e in records), default=None)
        expiry = max((e.expires_on for e in records if e.expires_on), default=None)
        missing.append(
            failing
            | {
                "last_given": given.isoformat() if given else None,
                "last_known_expiry": expiry.isoformat() if expiry else None,
            }
        )
    return {"missing": missing}


async def check_kennel_sizes(
    session: AsyncSession, ctx: ToolContext, args: CheckKennelSizes
) -> dict[str, Any]:
    _check_window(ctx, args.start_date, args.end_date)
    counts = await free_kennel_counts(session, ctx.facility_id, args.start_date, args.end_date)
    return {
        "pet_size_class": str(ctx.size_class),
        "free_by_size_class": {str(size): n for size, n in sorted(counts.items())},
    }


def check_offer(ctx: ToolContext, offer: ProposeOffer) -> None:
    """Rules an offer must meet to be accepted at all. Verification comes after."""
    for option in offer.options:
        if isinstance(option, LargerKennelOption):
            if ctx.species != Species.DOG:
                raise ToolError("larger_kennel applies only to dogs")
            if option.size_class not in DOG_SIZES or DOG_SIZES.index(
                option.size_class
            ) <= DOG_SIZES.index(ctx.size_class):
                raise ToolError(
                    f"larger_kennel must be a dog size larger than {ctx.size_class}, "
                    f"got {option.size_class}"
                )
        if isinstance(option, AlternativeDatesOption):
            if option.end_date < option.start_date:
                raise ToolError("alternative_dates: end_date is before start_date")
            _check_window(ctx, option.start_date, option.end_date)


Tool = Callable[[AsyncSession, ToolContext, Any], Awaitable[dict[str, Any]]]
READ_TOOLS: dict[str, tuple[type[BaseModel], Tool]] = {
    "find_alternative_dates": (FindAlternativeDates, find_alternative_dates),
    "list_missing_vaccines": (ListMissingVaccines, list_missing_vaccines),
    "check_kennel_sizes": (CheckKennelSizes, check_kennel_sizes),
}
PROPOSE = "propose_offer"
TOOL_SCHEMAS = [tool_schema(name, args) for name, (args, _) in READ_TOOLS.items()] + [
    tool_schema(PROPOSE, ProposeOffer)
]
