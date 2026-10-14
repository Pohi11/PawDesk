"""The comparison's alternative architecture: one autonomous agent with every tool and
authority over the outcome (spec: architecture-comparison, design D1).

Not part of PawDesk's workflow. It exists to be measured against it (decision record
0015). Its tools only read, and it writes nothing: its "decision" is just a result.
"""

import json
import uuid
from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from datetime import date
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.capacity import find_kennel
from app.compliance import VaccineEvidence, check, load_evidence, load_requirements
from app.enums import Service, SpanKind, Vaccine
from app.llm import ToolCall, complete
from app.models import Pet
from app.prompts.autonomous import PROMPT_VERSION, build_messages
from app.resolver import FindAlternativeDates, ToolContext, ToolError, find_alternative_dates
from app.resolver import tool_schema as _tool_schema
from app.structured import validation_errors
from app.tracing import span

MAX_TURNS = 12
MAX_TOOL_CALLS = 24
FINAL = "final_decision"
SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]


@dataclass(frozen=True)
class AgentContext:
    facility_id: uuid.UUID
    facility_name: str
    owner_id: uuid.UUID
    today: date
    message: str
    image: bytes | None = None
    mime: str | None = None


# --- Tool arguments ---------------------------------------------------------------------


class _Args(BaseModel):
    model_config = ConfigDict(extra="forbid")


PetName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class ListPets(_Args):
    """List the pets on file for the owner who sent this request."""


class CertificateRecord(_Args):
    vaccine: Vaccine
    administered_on: date = Field(description="YYYY-MM-DD, as printed.")
    expires_on: date | None = Field(description="YYYY-MM-DD as printed, or null if none.")


class CheckVaccines(_Args):
    """Check the pet's vaccines for a service and stay, using the records on file together
    with records you read from the certificate."""

    pet_name: PetName
    service: Service
    start_date: date = Field(description="First day on site, YYYY-MM-DD.")
    end_date: date = Field(description="Last day on site (checkout), YYYY-MM-DD.")
    certificate_records: list[CertificateRecord] = Field(max_length=20)


class CheckKennel(_Args):
    """Check whether a kennel of the pet's size is free for every night of a boarding stay."""

    pet_name: PetName
    start_date: date = Field(description="YYYY-MM-DD")
    end_date: date = Field(description="Checkout day, YYYY-MM-DD.")


class FindAlternatives(_Args):
    """Find nearby boarding stays of the same length with a free kennel."""

    pet_name: PetName
    start_date: date = Field(description="YYYY-MM-DD")
    end_date: date = Field(description="YYYY-MM-DD")
    max_shift_days: int = Field(ge=1, le=14)


Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
Reply = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1500)]


class FinalDecision(_Args):
    """Finish: confirm the booking, offer alternatives, or hand it to a person."""

    decision: Literal["confirm", "offer_alternatives", "needs_human"]
    reasons: list[Reason] = Field(min_length=1, max_length=10)
    reply: Reply = Field(description="The message to send to the pet parent.")


# --- Tools (read-only, bound to the owner and facility) --------------------------------


async def _pet(session: AsyncSession, ctx: AgentContext, name: str) -> Pet:
    pets = await session.scalars(select(Pet).where(Pet.owner_id == ctx.owner_id))
    match = [p for p in pets if p.name.casefold() == name.strip().casefold()]
    if not match:
        raise ToolError(f"no pet named {name!r} on file for this owner; call list_pets")
    return match[0]


async def list_pets(session: AsyncSession, ctx: AgentContext, _: ListPets) -> dict[str, Any]:
    pets = await session.scalars(select(Pet).where(Pet.owner_id == ctx.owner_id).order_by(Pet.name))
    return {
        "pets": [
            {"name": p.name, "species": str(p.species), "size_class": str(p.size_class)}
            for p in pets
        ]
    }


async def check_vaccines(
    session: AsyncSession, ctx: AgentContext, args: CheckVaccines
) -> dict[str, Any]:
    if args.end_date < args.start_date:
        raise ToolError("end_date is before start_date")
    pet = await _pet(session, ctx, args.pet_name)
    required = await load_requirements(session, ctx.facility_id, args.service, pet.species)
    given = [
        VaccineEvidence(r.vaccine, r.administered_on, r.expires_on)
        for r in args.certificate_records
    ]
    result = check(
        required, await load_evidence(session, pet.id) + given, args.start_date, args.end_date
    )
    return {
        "outcome": str(result.outcome),
        "vaccines": [{"vaccine": str(c.vaccine), "status": str(c.status)} for c in result.checks],
    }


async def check_kennel(
    session: AsyncSession, ctx: AgentContext, args: CheckKennel
) -> dict[str, Any]:
    if args.end_date <= args.start_date:
        raise ToolError("a kennel stay needs at least one night")
    pet = await _pet(session, ctx, args.pet_name)
    kennel = await find_kennel(
        session, ctx.facility_id, pet.size_class, args.start_date, args.end_date
    )
    return {
        "size_class": str(pet.size_class),
        "free": kennel is not None,
        "kennel": kennel.name if kennel else None,
    }


async def find_alternatives(
    session: AsyncSession, ctx: AgentContext, args: FindAlternatives
) -> dict[str, Any]:
    if args.end_date <= args.start_date:
        raise ToolError("a kennel stay needs at least one night")
    pet = await _pet(session, ctx, args.pet_name)
    # The same deterministic search the resolver uses, so both architectures share it.
    bound = ToolContext(
        facility_id=ctx.facility_id,
        species=pet.species,
        size_class=pet.size_class,
        service=Service.BOARDING,
        start=args.start_date,
        end=args.end_date,
        today=ctx.today,
        required=await load_requirements(session, ctx.facility_id, Service.BOARDING, pet.species),
        evidence=tuple(await load_evidence(session, pet.id)),
    )
    return await find_alternative_dates(
        session, bound, FindAlternativeDates(max_shift_days=args.max_shift_days)
    )


Tool = Callable[[AsyncSession, AgentContext, Any], Awaitable[dict[str, Any]]]
TOOLS: dict[str, tuple[type[BaseModel], Tool]] = {
    "list_pets": (ListPets, list_pets),
    "check_vaccines": (CheckVaccines, check_vaccines),
    "check_kennel": (CheckKennel, check_kennel),
    "find_alternative_dates": (FindAlternatives, find_alternatives),
}
TOOL_SCHEMAS = [_tool_schema(name, args) for name, (args, _) in TOOLS.items()] + [
    _tool_schema(FINAL, FinalDecision)
]


# --- The loop ---------------------------------------------------------------------------


@dataclass
class AgentRun:
    decision: str  # confirm | offer_alternatives | needs_human
    stop: str  # "final decision", or why the loop stopped early
    reasons: list[str] = field(default_factory=list)
    reply: str | None = None
    turns: int = 0
    tool_calls: list[dict[str, Any]] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "stop": self.stop,
            "reasons": self.reasons,
            "reply": self.reply,
            "turns": self.turns,
            "tool_calls": self.tool_calls,
            "prompt_version": PROMPT_VERSION,
        }


async def run_autonomous(
    sessions: SessionFactory, ctx: AgentContext, **llm_kwargs: Any
) -> AgentRun:
    async with span("autonomous", SpanKind.CODE, input={"message_chars": len(ctx.message)}) as s:
        s.attributes["prompt_version"] = PROMPT_VERSION
        result = await _loop(sessions, ctx, **llm_kwargs)
        s.output = {"decision": result.decision, "stop": result.stop, "turns": result.turns}
        return result


async def _loop(sessions: SessionFactory, ctx: AgentContext, **llm_kwargs: Any) -> AgentRun:
    messages = build_messages(
        facility=ctx.facility_name,
        today=ctx.today,
        message=ctx.message,
        image=ctx.image,
        mime=ctx.mime,
    )
    seen: set[tuple[str, str]] = set()
    calls: list[dict[str, Any]] = []

    def stop(reason: str, turn: int) -> AgentRun:
        return AgentRun("needs_human", reason, [], None, turn, calls)

    for turn in range(1, MAX_TURNS + 1):
        result = await complete(
            messages, name="autonomous.turn", tools=TOOL_SCHEMAS, temperature=0, **llm_kwargs
        )
        if not result.tool_calls:
            return stop("no decision: the model answered without calling a tool", turn)
        messages.append(result.assistant_message)
        for call in result.tool_calls:
            if len(calls) == MAX_TOOL_CALLS:
                return stop(f"step limit: {MAX_TOOL_CALLS} tool calls", turn)
            key = (call.name, _canonical(call.arguments))
            if key in seen:
                return stop(f"stuck: repeated {call.name} with the same arguments", turn)
            seen.add(key)
            content, final = await _run_call(sessions, ctx, call)
            calls.append(
                {"name": call.name, "arguments": call.arguments}
                | ({"error": content["error"]} if "error" in content else {})
            )
            if final is not None:
                return AgentRun(
                    final.decision, "final decision", final.reasons, final.reply, turn, calls
                )
            messages.append(
                {"role": "tool", "tool_call_id": call.id, "content": json.dumps(content)}
            )
    return stop(f"step limit: {MAX_TURNS} model calls", MAX_TURNS)


def _canonical(arguments: str) -> str:
    try:
        return json.dumps(json.loads(arguments), sort_keys=True)
    except ValueError:
        return arguments


async def _run_call(
    sessions: SessionFactory, ctx: AgentContext, call: ToolCall
) -> tuple[dict[str, Any], FinalDecision | None]:
    async with span(call.name, SpanKind.TOOL, input={"arguments": call.arguments}) as s:
        final = None
        try:
            raw = json.loads(call.arguments or "{}")
            if call.name == FINAL:
                final = FinalDecision.model_validate(raw)
                content: dict[str, Any] = {"accepted": True}
            elif call.name in TOOLS:
                args_model, tool = TOOLS[call.name]
                args = args_model.model_validate(raw)
                async with sessions() as session:
                    content = await tool(session, ctx, args)
            else:
                content = {
                    "error": f"unknown tool {call.name!r}; available: {', '.join([*TOOLS, FINAL])}"
                }
        except ValidationError as exc:
            content = {"error": "invalid arguments:\n" + validation_errors(exc)}
        except json.JSONDecodeError:
            content = {"error": "arguments are not valid JSON"}
        except ToolError as exc:
            content = {"error": str(exc)}
        s.output = content
        return content, final
