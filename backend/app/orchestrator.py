"""Drives a booking request from arrival to the message sent (spec: booking-orchestration;
decision records 0008 to 0011).

A hybrid workflow: code fixes the order of the steps, the models only read (intake and
records) or write (the reply), and every decision is plain code. The one agent (the
resolver) runs inside a fenced step and can only propose. Each step's result is saved in
the same transaction as the state change that follows it, so a crashed run resumes from
the request's state and reads saved results instead of redoing finished work.

    received -> extracting -> checking -> drafting -> ready -> approved -> sent
                                  |          ^      |                ^          ^
                                  v          |      v                | staff    |
                              resolving -----'   needs_review -------+----> rejected

Any working step can fail; the next run retries it. `needs_review` is not a step: a
request waiting there is left alone until a staff action moves it on.
"""

import asyncio
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.capacity import already_booked_reason, find_kennel, find_pet_stay
from app.compliance import Outcome, VaccineEvidence, check, load_evidence, load_requirements
from app.dates import facility_date
from app.documents import load_certificate
from app.enums import ApprovalAction, Service, SpanKind, Step, Vaccine
from app.intake import BookingIntent, IntakeResult, load_pets, run_intake
from app.lifecycle import Actor, State
from app.llm import LLMError
from app.models import (
    Approval,
    BookingRequest,
    BookingStepResult,
    Facility,
    OutboundMessage,
    Owner,
    Pet,
    Reservation,
)
from app.prompts.reply import PROMPT_VERSION as REPLY_PROMPT_VERSION
from app.records import RecordsResult, pet_name_mismatch, run_records
from app.reply import Situation, draft_reply, reply_facts
from app.resolver import (
    RequestFacts,
    ToolContext,
    not_attempted,
    request_facts,
    resolution_scope,
    resolve,
)
from app.structured import InvalidModelOutput
from app.tracing import Tracer, span
from app.transitions import transition

NO_CERTIFICATE = "no certificate provided"
PET_UNKNOWN = "pet unknown: compliance and capacity not checked"
STAY_UNUSABLE = "service or dates unusable: compliance and capacity not checked"

MAX_ERROR_CHARS = 1000

# Expected ways for a step to fail: the model was unavailable, or its output stayed invalid
# after the repair attempt. These move the request to `failed`, to be retried. Anything else
# is a bug: it propagates and leaves the request in its working state (design D6).
STEP_ERRORS = (LLMError, InvalidModelOutput)


class StepFailed(Exception):
    """One or both extraction steps failed in an expected way (see STEP_ERRORS)."""


# Called with the state whose work just committed (tests and the command line use it to
# stop a run at a chosen checkpoint, like a killed process would).
CrashHook = Callable[[State], None]


@dataclass
class _Run:
    request_id: uuid.UUID
    sessions: async_sessionmaker[AsyncSession]
    today: date | None
    crash_after: CrashHook | None
    llm_kwargs: dict[str, Any] = field(default_factory=dict)

    def checkpoint(self, state: State) -> None:
        if self.crash_after is not None:
            self.crash_after(state)


async def process_request(
    request_id: uuid.UUID,
    *,
    sessions: async_sessionmaker[AsyncSession],
    tracer: Tracer | None = None,
    today: date | None = None,
    crash_after: CrashHook | None = None,
    **llm_kwargs: Any,
) -> State:
    """Advance the request as far as this phase goes and return the state it ends in.

    `today` is the facility-local date (computed from the facility's time zone when None).
    `llm_kwargs` pass through to the model client (client, settings, policy) for tests.
    """
    status, failed_step = await _status(sessions, request_id)
    retryable = status == State.FAILED and failed_step in STEPS
    if status not in STEPS and not retryable:
        return status  # finished or waiting on a later phase: nothing to do, nothing traced

    run = _Run(request_id, sessions, today, crash_after, llm_kwargs)
    tracer = tracer or Tracer(sessions)
    await tracer.close_abandoned(request_id)  # left open by an earlier run that was killed
    async with tracer.start_trace("process booking", booking_request_id=request_id):
        if retryable:
            status = await _retry(run, failed_step)
        while status in STEPS:
            previous = status
            try:
                status = await STEPS[status](run)
            except (StepFailed, *STEP_ERRORS) as exc:
                # Stop here. Retrying straight away would usually fail the same way; the
                # next run retries from the failed step.
                return await _fail(run, exc)
            run.checkpoint(previous)
    return status


async def _status(
    sessions: async_sessionmaker[AsyncSession], request_id: uuid.UUID
) -> tuple[State, State | None]:
    async with sessions() as session:
        row = (
            await session.execute(
                select(BookingRequest.status, BookingRequest.failed_step).where(
                    BookingRequest.id == request_id
                )
            )
        ).one_or_none()
    if row is None:
        raise LookupError(f"no booking request {request_id}")
    return row.status, row.failed_step


async def _retry(run: _Run, failed_step: State) -> State:
    async with run.sessions() as session:
        request = await session.get_one(BookingRequest, run.request_id)
        await transition(session, request, failed_step, Actor.SYSTEM, reason="retry")
        await session.commit()
    return failed_step


async def _fail(run: _Run, exc: Exception) -> State:
    # A fresh session: whatever the failed step had in flight was never committed.
    error = str(exc) if isinstance(exc, StepFailed) else f"{type(exc).__name__}: {exc}"
    async with run.sessions() as session:
        request = await session.get_one(BookingRequest, run.request_id)
        await transition(
            session, request, State.FAILED, Actor.SYSTEM, error=error[:MAX_ERROR_CHARS]
        )
        await session.commit()
    return State.FAILED


# --- Steps: each one commits its work and the state change together -------------------


async def _start(run: _Run) -> State:
    async with run.sessions() as session:
        request = await session.get_one(BookingRequest, run.request_id)
        # Committed before any model call, so a crash during extraction resumes there.
        await transition(session, request, State.EXTRACTING, Actor.SYSTEM)
        await session.commit()
    return State.EXTRACTING


@dataclass(frozen=True)
class _ExtractionInputs:
    message: str
    pets: list
    timezone: str
    certificate: bytes | None


async def _extract(run: _Run) -> State:
    # Read everything first, then let go of the session: no connection is held open while
    # the models work, and the two concurrent steps never share a session (design D4).
    async with run.sessions() as session:
        request = await session.get_one(BookingRequest, run.request_id)
        facility = await session.get_one(Facility, request.facility_id)
        document = await load_certificate(session, request.id)
        inputs = _ExtractionInputs(
            message=request.raw_message,
            pets=await load_pets(session, request.owner_id),
            timezone=facility.timezone,
            certificate=document.content if document else None,
        )
    today = run.today or facility_date(inputs.timezone, datetime.now(UTC))

    async with span("extract", SpanKind.CODE, input={"certificate": bool(inputs.certificate)}) as s:
        intake, records = await asyncio.gather(
            run_intake(
                inputs.message,
                pets=inputs.pets,
                today=today,
                timezone=inputs.timezone,
                **run.llm_kwargs,
            ),
            _records_or_skip(inputs, today, run.llm_kwargs),
            return_exceptions=True,  # let both finish, so neither leaves a span open
        )
        _raise_failures(intake=intake, records=records)
        outputs = {Step.INTAKE: _intake_output(intake), Step.RECORDS: _records_output(records)}
        s.output = {str(step): out["outcome"] for step, out in outputs.items()}

    async with run.sessions() as session:
        request = await session.get_one(BookingRequest, run.request_id)
        request.pet_id = intake.pet_id
        session.add_all(
            BookingStepResult(booking_request_id=request.id, step=step, output=out)
            for step, out in outputs.items()
        )
        await transition(session, request, State.CHECKING, Actor.SYSTEM)
        await session.commit()
    return State.CHECKING


def _raise_failures(**results: object) -> None:
    """Re-raise a bug or a cancellation as is; report expected failures from either step
    together, so the recorded error names every step that failed."""
    expected = []
    for name, result in results.items():
        if isinstance(result, STEP_ERRORS):
            expected.append(f"{name}: {type(result).__name__}: {result}")
        elif isinstance(result, BaseException):
            raise result
    if expected:
        raise StepFailed("; ".join(expected))


async def _records_or_skip(
    inputs: _ExtractionInputs, today: date, llm_kwargs: dict[str, Any]
) -> RecordsResult | None:
    if inputs.certificate is None:
        return None
    # The booked pet isn't known until intake finishes, and intake runs alongside this
    # step, so the pet-name comparison happens in the checking step instead (design D3).
    return await run_records(
        inputs.certificate, booked_pet=None, today=today, timezone=inputs.timezone, **llm_kwargs
    )


async def _check_and_route(run: _Run) -> State:
    async with run.sessions() as session:
        request = await session.get_one(BookingRequest, run.request_id)
        saved = await _saved_results(session, request.id)
        intake, records = saved[Step.INTAKE], saved[Step.RECORDS]

        async with span("check", SpanKind.CODE) as s:
            checks = await _checks(session, request, intake, records)
            s.output = checks
        async with span("route", SpanKind.CODE) as s:
            target, reasons = decide_route(intake, records, checks)
            s.output = {"target": target, "reasons": reasons}

        session.add_all(
            [
                BookingStepResult(booking_request_id=request.id, step=Step.CHECKS, output=checks),
                BookingStepResult(
                    booking_request_id=request.id,
                    step=Step.ROUTE,
                    output={"target": target, "reasons": reasons},
                ),
            ]
        )
        reason = "; ".join(reasons) if reasons else "all checks clear"
        await transition(session, request, target, Actor.SYSTEM, reason=reason)
        await session.commit()
    return target


async def _resolve(run: _Run) -> State:
    # As in extraction: read first, then let the session go. The loop's tools open short
    # sessions of their own, so no connection waits on the model.
    async with run.sessions() as session:
        request = await session.get_one(BookingRequest, run.request_id)
        saved = await _saved_results(session, request.id)
        scope = resolution_scope(saved[Step.INTAKE], saved[Step.RECORDS], saved[Step.CHECKS])
        inputs = (
            await _resolver_inputs(session, request, saved, run.today) if scope.eligible else None
        )

    async with span("resolve", SpanKind.CODE, input={"eligible": scope.eligible}) as s:
        if inputs is None:
            resolution = not_attempted(scope)  # code decided: no model call at all
        else:
            ctx, facts = inputs
            resolution = await resolve(run.sessions, ctx, facts, scope, **run.llm_kwargs)
        s.output = {
            "outcome": str(resolution.outcome),
            "reason": resolution.reason,
            "turns": resolution.turns,
        }

    async with run.sessions() as session:
        request = await session.get_one(BookingRequest, run.request_id)
        session.add(
            BookingStepResult(
                booking_request_id=request.id, step=Step.RESOLUTION, output=resolution.to_json()
            )
        )
        reason = f"resolution {resolution.outcome}: {resolution.reason}"
        await transition(session, request, State.DRAFTING, Actor.SYSTEM, reason=reason)
        await session.commit()
    return State.DRAFTING


async def _resolver_inputs(
    session: AsyncSession, request: BookingRequest, saved: dict[Step, dict], today: date | None
) -> tuple[ToolContext, RequestFacts]:
    pet = await session.get_one(Pet, request.pet_id)
    facility = await session.get_one(Facility, request.facility_id)
    today = today or facility_date(facility.timezone, datetime.now(UTC))
    facts = request_facts(saved[Step.INTAKE], str(pet.species), str(pet.size_class), today)
    service = Service(facts.service)
    on_file = await load_evidence(session, pet.id)
    ctx = ToolContext(
        facility_id=facility.id,
        species=pet.species,
        size_class=pet.size_class,
        service=service,
        start=facts.start,
        end=facts.end,
        today=today,
        required=await load_requirements(session, facility.id, service, pet.species),
        evidence=tuple(on_file + _evidence(saved[Step.RECORDS])),
        pet_id=pet.id,
    )
    return ctx, facts


async def _draft(run: _Run) -> State:
    async with run.sessions() as session:
        request = await session.get_one(BookingRequest, run.request_id)
        saved = await _saved_results(session, request.id)
        owner = await session.get_one(Owner, request.owner_id)
        facility = await session.get_one(Facility, request.facility_id)
        pet = await session.get(Pet, request.pet_id) if request.pet_id else None
        facts = reply_facts(
            owner_name=owner.full_name,
            pet_name=pet.name if pet else None,
            facility=facility.name,
            intake=saved[Step.INTAKE],
            route=saved[Step.ROUTE],
            resolution=saved.get(Step.RESOLUTION),
        )

    result = await draft_reply(facts, **run.llm_kwargs)  # no session held during the call

    # Code decides who sends it (decision record 0011): anything that needed resolving, or
    # a draft that over-promises, waits for a person.
    flags = []
    if saved[Step.ROUTE]["target"] == State.RESOLVING:
        resolution = saved.get(Step.RESOLUTION) or {}
        flags.append(
            f"came through resolving: {resolution.get('outcome')} ({resolution.get('reason')})"
        )
    flags += [f"reply: {issue}" for issue in result.promise_issues]
    target = State.NEEDS_REVIEW if flags else State.READY

    async with run.sessions() as session:
        request = await session.get_one(BookingRequest, run.request_id)
        session.add(
            BookingStepResult(
                booking_request_id=request.id,
                step=Step.REPLY,
                output={
                    "situation": str(facts.situation),
                    "facts": facts.to_json(),
                    "draft": result.draft.model_dump(),
                    "promise_issues": result.promise_issues,
                    "flags": flags,
                    "target": str(target),
                    "prompt_version": REPLY_PROMPT_VERSION,
                },
            )
        )
        reason = (
            "; ".join(flags)
            if flags
            else "clean: every check passed and the reply promises nothing more"
        )
        await transition(session, request, target, Actor.SYSTEM, reason=reason)
        await session.commit()
    return target


async def _auto_approve(run: _Run) -> State:
    async with run.sessions() as session:
        request = await session.get_one(BookingRequest, run.request_id)
        await transition(
            session,
            request,
            State.APPROVED,
            Actor.SYSTEM,
            reason="clean request: approved by the checks",
        )
        await session.commit()
    return State.APPROVED


async def _send(run: _Run) -> State:
    """Record the outbound message (and, for a confirmed stay, the reservation) together
    with the move to `sent`. Both are unique per request, so a retry can't double up."""
    async with run.sessions() as session:
        request = await session.get_one(BookingRequest, run.request_id)
        saved = await _saved_results(session, request.id)
        reply = saved[Step.REPLY]

        if request.status == State.APPROVED:
            approval = await session.scalar(
                select(Approval)
                .where(Approval.booking_request_id == request.id)
                .order_by(Approval.created_at.desc(), Approval.id.desc())
                .limit(1)
            )
            edited = approval is not None and approval.action == ApprovalAction.EDIT_AND_APPROVE
            kind, subject = "reply", reply["draft"]["subject"]
            body = approval.edited_reply if edited else reply["draft"]["body"]
            await _reserve_if_confirmed(session, request, reply)
        else:
            kind, (subject, body) = "decline", decline_message(reply["facts"])

        session.add(
            OutboundMessage(booking_request_id=request.id, kind=kind, subject=subject, body=body)
        )
        await transition(session, request, State.SENT, Actor.SYSTEM, reason=f"{kind} sent")
        await session.commit()
    return State.SENT


async def _reserve_if_confirmed(
    session: AsyncSession, request: BookingRequest, reply: dict
) -> None:
    facts = reply["facts"]
    if reply["situation"] != Situation.CONFIRMED or facts["service"] != Service.BOARDING:
        return
    start, end = date.fromisoformat(facts["start_date"]), date.fromisoformat(facts["end_date"])
    pet = await session.get_one(Pet, request.pet_id)
    # Checked again now: the pet may have been booked, or the kennel taken, since checking.
    if await find_pet_stay(session, pet.id, start, end) is not None:
        raise StepFailed(f"{pet.name} already has a kennel for these nights at send time")
    kennel = await find_kennel(session, request.facility_id, pet.size_class, start, end)
    if kennel is None:
        raise StepFailed(f"no free {pet.size_class} kennel at send time")
    session.add(
        Reservation(
            kennel_id=kennel.id,
            pet_id=pet.id,
            booking_request_id=request.id,
            start_date=start,
            end_date=end,
        )
    )
    try:
        await session.flush()
    except IntegrityError as exc:
        # Another transaction reserved the same kennel, or this pet, between our search and
        # this insert; the exclusion constraints are the real guarantee against double-booking.
        if "ex_reservations_no_overlapping_stays" in str(exc):
            raise StepFailed("kennel taken at send time by another booking") from exc
        if "ex_reservations_one_kennel_per_pet" in str(exc):
            raise StepFailed("pet booked at send time by another booking") from exc
        raise


def decline_message(facts: dict) -> tuple[str, str]:
    """A fixed decline filled by code. The staff member's internal reason is never sent."""
    subject = "Your booking request"
    body = (
        f"Hi {facts['owner_first_name']},\n\n"
        f"Thank you for your request for {facts['pet_name']}. Unfortunately, we aren't able "
        "to accept this booking request. If anything changes, a member of our team will be "
        f"in touch.\n\nThe {facts['facility']} team"
    )
    return subject, body


STEPS = {
    State.RECEIVED: _start,
    State.EXTRACTING: _extract,
    State.CHECKING: _check_and_route,
    State.RESOLVING: _resolve,
    State.DRAFTING: _draft,
    State.READY: _auto_approve,
    State.APPROVED: _send,
    State.REJECTED: _send,
}


async def _saved_results(session: AsyncSession, request_id: uuid.UUID) -> dict[Step, dict]:
    rows = await session.execute(
        select(BookingStepResult.step, BookingStepResult.output).where(
            BookingStepResult.booking_request_id == request_id
        )
    )
    return {Step(step): output for step, output in rows}


# --- Saved step outputs (plain JSON, so a resumed run needs nothing else) --------------


def _intake_output(result: IntakeResult) -> dict[str, Any]:
    return {
        "intent": result.intent.model_dump(mode="json") if result.intent else None,
        "pet_id": str(result.pet_id) if result.pet_id else None,
        "issues": list(result.issues),
        "outcome": str(result.outcome),
    }


def _records_output(result: RecordsResult | None) -> dict[str, Any]:
    if result is None:
        return {
            "skipped": NO_CERTIFICATE,
            "extraction": None,
            "evidence": [],
            "issues": [],
            "outcome": "skipped",
        }
    return {
        "skipped": None,
        "extraction": result.extraction.model_dump(mode="json") if result.extraction else None,
        "evidence": [
            {
                "vaccine": str(e.vaccine),
                "administered_on": e.administered_on.isoformat(),
                "expires_on": e.expires_on.isoformat() if e.expires_on else None,
            }
            for e in result.evidence
        ],
        "issues": list(result.issues),
        "outcome": str(result.outcome),
    }


def _evidence(records: dict[str, Any]) -> list[VaccineEvidence]:
    return [
        VaccineEvidence(
            Vaccine(e["vaccine"]),
            date.fromisoformat(e["administered_on"]),
            date.fromisoformat(e["expires_on"]) if e["expires_on"] else None,
        )
        for e in records["evidence"]
    ]


# --- Checks and routing: deterministic code ---------------------------------------------


async def _checks(
    session: AsyncSession, request: BookingRequest, intake: dict, records: dict
) -> dict[str, Any]:
    pet = await session.get(Pet, request.pet_id) if request.pet_id else None
    certificate_name = (records["extraction"] or {}).get("pet_name")
    checks: dict[str, Any] = {
        "pet": {
            "id": str(pet.id) if pet else None,
            "name": pet.name if pet else None,
            "certificate_name": certificate_name,
            "mismatch": pet_name_mismatch(certificate_name, pet.name if pet else None),
        },
        "not_checked": None,
        "compliance": None,
        "capacity": None,
    }

    intent = BookingIntent.model_validate(intake["intent"]) if intake["intent"] else None
    if pet is None:
        checks["not_checked"] = PET_UNKNOWN
        return checks
    if (
        intent is None
        or intent.service is None
        or intent.start_date is None
        or intent.end_date is None
        or intent.end_date < intent.start_date
    ):
        checks["not_checked"] = STAY_UNUSABLE
        return checks

    service, start, end = intent.service, intent.start_date, intent.end_date
    on_file = await load_evidence(session, pet.id)
    from_certificate = _evidence(records)
    async with span("compliance", SpanKind.CODE) as s:
        required = await load_requirements(session, request.facility_id, service, pet.species)
        result = check(required, on_file + from_certificate, start, end)
        checks["compliance"] = {
            "outcome": str(result.outcome),
            "checks": [{"vaccine": str(c.vaccine), "status": str(c.status)} for c in result.checks],
            "records_on_file": len(on_file),
            "records_from_certificate": len(from_certificate),
        }
        s.output = checks["compliance"]

    checks["capacity"] = await _capacity(session, request.facility_id, pet, service, start, end)
    return checks


async def _capacity(
    session: AsyncSession, facility_id: uuid.UUID, pet: Pet, service: Service, start, end
) -> dict[str, Any]:
    if service != Service.BOARDING:
        return {"status": "not_needed", "size_class": None, "kennel": None}
    if end <= start:
        # Intake already reports "boarding needs at least one night".
        return {"status": "not_checked", "size_class": str(pet.size_class), "kennel": None}
    async with span("capacity", SpanKind.TOOL, input={"size_class": str(pet.size_class)}) as s:
        # A pet already staying those nights is not booked again (change one-kennel-per-pet).
        if await find_pet_stay(session, pet.id, start, end) is not None:
            result = {"status": "already_booked", "size_class": str(pet.size_class), "kennel": None}
            s.output = result
            return result
        kennel = await find_kennel(session, facility_id, pet.size_class, start, end)
        result = {
            "status": "found" if kennel else "none_free",
            "size_class": str(pet.size_class),
            "kennel": kennel.name if kennel else None,
        }
        s.output = result
    return result


def decide_route(intake: dict, records: dict, checks: dict) -> tuple[State, list[str]]:
    """`drafting` only when nothing needs a closer look; otherwise `resolving`, with every
    reason listed. Pure: the same saved results always route the same way."""
    reasons = [f"intake: {issue}" for issue in intake["issues"]]
    reasons += [f"records: {issue}" for issue in records["issues"]]
    if checks["not_checked"]:
        reasons.append(checks["not_checked"])
    if checks["pet"]["mismatch"]:
        reasons.append(checks["pet"]["mismatch"])

    compliance = checks["compliance"]
    if compliance and compliance["outcome"] != Outcome.COMPLIANT:
        reasons += [
            f"vaccine {c['vaccine']}: {c['status']}"
            for c in compliance["checks"]
            if c["status"] != "ok"
        ]
    capacity = checks["capacity"]
    if capacity and capacity["status"] == "none_free":
        reasons.append(f"capacity: no free {capacity['size_class']} kennel for the stay")
    if capacity and capacity["status"] == "not_checked":
        reasons.append("capacity: not checked")
    if capacity and capacity["status"] == "already_booked":
        reasons.append(already_booked_reason(checks["pet"]["name"]))

    return (State.RESOLVING if reasons else State.DRAFTING), reasons
