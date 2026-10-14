"""Booking intake: untrusted pet-parent message -> validated intent + issues.

Spec: booking-intake. The model only *describes* the request; code decides identity
(pet matching), timing (date checks), and whether a person must look (issues).
"""

import copy
import re
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import Service, SpanKind
from app.llm import complete
from app.models import Pet
from app.prompts.intake import PROMPT_VERSION, build_messages
from app.tracing import span

Ambiguity = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class BookingIntent(BaseModel):
    """What the model must return. `extra="forbid"`: any unexpected field (say, an injected
    `"approved": true`) fails validation instead of being silently dropped."""

    model_config = ConfigDict(extra="forbid")

    pet_name: str | None = Field(description="The pet's name as written, or null if not given.")
    service: Service | None = Field(description="boarding, daycare, or grooming; null if unclear.")
    start_date: date | None = Field(description="First day on site, YYYY-MM-DD, or null.")
    end_date: date | None = Field(
        description="Last day on site (checkout day), YYYY-MM-DD, or null."
    )
    special_notes: str = Field(
        max_length=500, description="Care notes from the customer (diet, meds, behavior)."
    )
    confidence: float = Field(ge=0, le=1, description="How sure you are, from 0 to 1.")
    ambiguities: list[Ambiguity] = Field(
        max_length=10, description="Anything unclear or conflicting; empty if none."
    )


# Keys some providers' strict modes reject. Pydantic still enforces the real constraints.
_DROP_KEYS = {
    "title",
    "default",
    "format",
    "minimum",
    "maximum",
    "maxLength",
    "minLength",
    "maxItems",
    "minItems",
}


def _strictify(node: Any, defs: dict[str, Any]) -> Any:
    if isinstance(node, list):
        return [_strictify(item, defs) for item in node]
    if not isinstance(node, dict):
        return node
    if "$ref" in node:  # inline $defs: simplest form for every provider
        return _strictify(copy.deepcopy(defs[node["$ref"].rsplit("/", 1)[-1]]), defs)
    out = {k: _strictify(v, defs) for k, v in node.items() if k not in _DROP_KEYS}
    if out.get("type") == "object" and "properties" in out:
        out["required"] = list(out["properties"])  # strict mode: every field required
        out["additionalProperties"] = False
    return out


def strict_json_schema(model: type[BaseModel]) -> dict[str, Any]:
    """The provider-side schema, derived from the same model that validates (design D1)."""
    schema = model.model_json_schema()
    defs = schema.pop("$defs", {})
    schema.pop("description", None)  # the class docstring is for developers, not the model
    return _strictify(schema, defs)


def response_format() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "booking_intent",
            "strict": True,
            "schema": strict_json_schema(BookingIntent),
        },
    }


# --- The pipeline (design D2–D6) ------------------------------------------------------

MAX_MESSAGE_CHARS = 4000
CONFIDENCE_THRESHOLD = 0.7
BOOKING_HORIZON_DAYS = 365

INSTRUCTION_LIKE_ISSUE = "message contains instruction-like text"
# Deliberately narrow (design D5b): a match only ever costs a human review.
INSTRUCTION_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bignore\b[^.\n]{0,40}\b(instructions?|rules|prompts?)\b",
        r"\b(system|assistant|developer)\s*:",
        r"\bconfidence\s*[:=]",
        r"\bno\s+(human\s+)?review\b",
        r"\b(skip|bypass)\b[^.\n]{0,20}\breview\b",
        r"\bmark\b[^.\n]{0,30}\bapproved\b",
        r"\byou are now\b",
    )
]

REPAIR_INSTRUCTION = (
    "Your previous output failed validation:\n{errors}\n"
    "Return only the corrected JSON object, with every field."
)


class IntakeOutcome(StrEnum):
    CLEAR = "clear"
    NEEDS_REVIEW = "needs_review"


class IntakeInvalidOutput(Exception):
    """The model's output failed validation, and so did the one repair attempt."""


@dataclass(frozen=True)
class PetRef:
    id: uuid.UUID
    name: str


@dataclass(frozen=True)
class IntakeResult:
    """Everything intake can say. Nothing here can approve, price, or prioritize."""

    intent: BookingIntent | None
    pet_id: uuid.UUID | None
    issues: tuple[str, ...]
    outcome: IntakeOutcome


def instruction_like(message: str) -> bool:
    return any(pattern.search(message) for pattern in INSTRUCTION_PATTERNS)


def date_issues(intent: BookingIntent, today: date) -> list[str]:
    start, end = intent.start_date, intent.end_date
    if start is None or end is None:
        return ["dates missing"]
    issues = []
    if end < start:
        issues.append("end date is before start date")
    if start < today:
        issues.append("start date is in the past")
    if start > today + timedelta(days=BOOKING_HORIZON_DAYS):
        issues.append(f"start date is more than {BOOKING_HORIZON_DAYS} days away")
    if intent.service == Service.BOARDING and end == start:
        issues.append("boarding needs at least one night")
    if intent.service in (Service.DAYCARE, Service.GROOMING) and end != start:
        issues.append(f"{intent.service} request spans more than one day")
    return issues


def match_pet(name: str | None, pets: Sequence[PetRef]) -> tuple[uuid.UUID | None, str | None]:
    if not name or not name.strip():
        return None, "pet not named"
    wanted = name.strip().casefold()
    matches = [p for p in pets if p.name.strip().casefold() == wanted]
    if len(matches) == 1:
        return matches[0].id, None
    if not matches:
        return None, f"no pet named {name.strip()!r} on file for this owner"
    return None, f"several pets named {name.strip()!r} on file"


def _validation_errors(exc: ValidationError) -> str:
    lines = [f"- {'.'.join(map(str, e['loc'])) or 'output'}: {e['msg']}" for e in exc.errors()]
    return "\n".join(lines)[:1000]


async def _extract(messages: list[dict[str, str]], **llm_kwargs: Any) -> tuple[BookingIntent, bool]:
    """Call the model, validate, and repair once (design D3). Returns (intent, repaired)."""
    common = {"response_format": response_format(), "temperature": 0, **llm_kwargs}
    first = await complete(messages, name="intake.extract", **common)
    try:
        return BookingIntent.model_validate_json(first.text), False
    except ValidationError as exc:
        errors = _validation_errors(exc)

    repair_messages = [
        *messages,
        {"role": "assistant", "content": first.text},
        {"role": "user", "content": REPAIR_INSTRUCTION.format(errors=errors)},
    ]
    second = await complete(repair_messages, name="intake.repair", **common)
    try:
        return BookingIntent.model_validate_json(second.text), True
    except ValidationError as exc:
        raise IntakeInvalidOutput(
            f"intake output invalid after repair: {_validation_errors(exc)}"
        ) from exc


async def run_intake(
    message: str,
    *,
    pets: Sequence[PetRef],
    today: date,
    timezone: str,
    **llm_kwargs: Any,
) -> IntakeResult:
    """`today` is the facility-local date (see app.dates.facility_date). `llm_kwargs` pass
    through to complete() (client, settings, policy) for tests."""
    async with span("intake", SpanKind.CODE, input={"message_chars": len(message)}) as s:
        s.attributes["prompt_version"] = PROMPT_VERSION

        if len(message) > MAX_MESSAGE_CHARS:
            result = IntakeResult(
                intent=None,
                pet_id=None,
                issues=(f"message longer than {MAX_MESSAGE_CHARS} characters; not processed",),
                outcome=IntakeOutcome.NEEDS_REVIEW,
            )
            s.output = _span_output(result, repaired=False)
            return result

        issues: list[str] = []
        if instruction_like(message):  # decided in code, before the model sees anything
            issues.append(INSTRUCTION_LIKE_ISSUE)

        intent, repaired = await _extract(build_messages(message, today, timezone), **llm_kwargs)

        issues += date_issues(intent, today)
        pet_id, pet_issue = match_pet(intent.pet_name, pets)
        if pet_issue:
            issues.append(pet_issue)
        if intent.service is None:
            issues.append("service missing")
        # Confidence can only add caution, never remove it (design D5).
        if intent.confidence < CONFIDENCE_THRESHOLD:
            issues.append(f"low confidence ({intent.confidence:.2f})")
        issues += [f"ambiguous: {a}" for a in intent.ambiguities]

        result = IntakeResult(
            intent=intent,
            pet_id=pet_id,
            issues=tuple(issues),
            outcome=IntakeOutcome.NEEDS_REVIEW if issues else IntakeOutcome.CLEAR,
        )
        s.output = _span_output(result, repaired=repaired)
        return result


def _span_output(result: IntakeResult, *, repaired: bool) -> dict[str, Any]:
    return {
        "intent": result.intent.model_dump(mode="json") if result.intent else None,
        "pet_id": str(result.pet_id) if result.pet_id else None,
        "issues": list(result.issues),
        "outcome": result.outcome,
        "repaired": repaired,
    }


async def load_pets(session: AsyncSession, owner_id: uuid.UUID) -> list[PetRef]:
    rows = await session.execute(select(Pet.id, Pet.name).where(Pet.owner_id == owner_id))
    return [PetRef(*row) for row in rows]
