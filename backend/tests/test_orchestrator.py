"""Spec: booking-orchestration, against scripted model answers and a real database."""

import asyncio
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import select

from app import orchestrator
from app.documents import attach_certificate
from app.enums import Service, Species, Step, Vaccine
from app.lifecycle import State
from app.llm import RetryPolicy, make_client
from app.models import (
    BookingRequest,
    BookingStepResult,
    BookingTransition,
    Facility,
    Kennel,
    Owner,
    Pet,
    Reservation,
    Span,
    Trace,
    VaccineRecord,
    VaccineRule,
)
from app.orchestrator import NO_CERTIFICATE, PET_UNKNOWN, process_request
from tests.test_llm import fail, fake_settings, ok

spec = pytest.mark.spec
TODAY = date(2027, 3, 3)
START, END = date(2027, 3, 10), date(2027, 3, 14)
PNG = b"\x89PNG\r\n\x1a\n" + b"synthetic certificate pixels " * 50

INTENT = {
    "pet_name": "Biscuit",
    "service": "boarding",
    "start_date": START.isoformat(),
    "end_date": END.isoformat(),
    "special_notes": "",
    "confidence": 0.95,
    "ambiguities": [],
}
BORDETELLA = {
    "label": "Bordetella",
    "vaccine": "bordetella",
    "administered_on": "2026-09-01",
    "expires_on": "2027-09-01",
}
CERTIFICATE = {
    "pet_name": "Biscuit",
    "records": [BORDETELLA],
    "readable": True,
    "confidence": 0.95,
    "ambiguities": [],
}


class FakeModel:
    """Answers intake and records calls separately, since they arrive concurrently and in
    no fixed order. Each answer is a dict (returned as JSON) or an HTTP error status; the
    last answer of each kind repeats."""

    def __init__(self, intake=INTENT, records=CERTIFICATE, delay=0.0):
        self.answers = {"intake": _listed(intake), "records": _listed(records)}
        self.calls = {"intake": 0, "records": 0}
        self.delay = delay

    @property
    def total_calls(self) -> int:
        return sum(self.calls.values())

    async def __call__(self, request: httpx.Request) -> httpx.Response:
        kind = "records" if b"vaccine_certificate" in request.content else "intake"
        self.calls[kind] += 1
        await asyncio.sleep(self.delay)
        queue = self.answers[kind]
        answer = queue.pop(0) if len(queue) > 1 else queue[0]
        return fail(answer) if isinstance(answer, int) else ok(text=json.dumps(answer))


def _listed(answer):
    return list(answer) if isinstance(answer, list) else [answer]


@dataclass
class Desk:
    facility_id: object
    owner_id: object
    biscuit_id: object
    olive_id: object
    kennel_id: object


@pytest.fixture
async def desk(committed) -> Desk:
    """A facility with one owner, Biscuit (medium dog) and Olive (cat), one medium kennel,
    and Biscuit's records on file: rabies and DHPP, but no bordetella."""
    async with committed() as s:
        facility = Facility(name="Test Lodge", timezone="America/Chicago")
        owner = Owner(full_name="Test Owner", email="orchestrator@example.test")
        s.add_all([facility, owner])
        await s.flush()
        biscuit = Pet(owner_id=owner.id, name="Biscuit", species=Species.DOG, weight_lb=35)
        olive = Pet(owner_id=owner.id, name="Olive", species=Species.CAT, weight_lb=9)
        kennel = Kennel(facility_id=facility.id, name="M1", size_class="medium")
        s.add_all([biscuit, olive, kennel])
        await s.flush()
        s.add_all(
            [
                VaccineRule(
                    facility_id=facility.id, service=service, species=Species.DOG, vaccine=v
                )
                for service, vaccines in {
                    Service.BOARDING: [Vaccine.RABIES, Vaccine.DHPP, Vaccine.BORDETELLA],
                    Service.GROOMING: [Vaccine.RABIES],
                }.items()
                for v in vaccines
            ]
            + [
                VaccineRecord(
                    pet_id=biscuit.id,
                    vaccine=v,
                    administered_on=date(2026, 4, 1),
                    expires_on=date(2028, 4, 1),
                )
                for v in (Vaccine.RABIES, Vaccine.DHPP)
            ]
        )
        await s.commit()
        return Desk(facility.id, owner.id, biscuit.id, olive.id, kennel.id)


@pytest.fixture
def submit(committed, desk):
    async def make(message="Can Biscuit board March 10 to 14?", certificate=PNG):
        async with committed() as s:
            request = BookingRequest(
                facility_id=desk.facility_id, owner_id=desk.owner_id, raw_message=message
            )
            s.add(request)
            await s.flush()
            if certificate is not None:
                await attach_certificate(s, request.id, certificate)
            await s.commit()
            return request.id

    return make


async def _no_sleep(_seconds):
    return None


@pytest.fixture
def process(committed, tracer):
    async def run(request_id, model, **kwargs):
        settings = fake_settings()
        client = make_client(settings, transport=httpx.MockTransport(model))
        return await process_request(
            request_id,
            sessions=committed,
            tracer=tracer,
            today=TODAY,
            client=client,
            settings=settings,
            policy=RetryPolicy(max_attempts=2, sleep=_no_sleep),
            **kwargs,
        )

    return run


async def saved(committed, request_id) -> dict:
    async with committed() as s:
        rows = await s.execute(
            select(BookingStepResult.step, BookingStepResult.output).where(
                BookingStepResult.booking_request_id == request_id
            )
        )
        return {Step(step): output for step, output in rows}


async def states(committed, request_id) -> list[State]:
    async with committed() as s:
        rows = await s.scalars(
            select(BookingTransition.to_status)
            .where(BookingTransition.booking_request_id == request_id)
            .order_by(BookingTransition.created_at, BookingTransition.id)
        )
        return list(rows)


async def spans_of(committed, request_id) -> list[Span]:
    async with committed() as s:
        rows = await s.scalars(
            select(Span)
            .join(Trace, Trace.id == Span.trace_id)
            .where(Trace.booking_request_id == request_id)
            .order_by(Span.started_at, Span.id)
        )
        return list(rows)


# --- Extraction runs intake and records concurrently -----------------------------------


@spec("booking-orchestration", "Extraction runs intake and records concurrently")
async def test_both_extraction_steps_start_before_either_ends(committed, submit, process):
    request_id = await submit()

    await process(request_id, FakeModel(delay=0.3))

    by_name = {s.name: s for s in await spans_of(committed, request_id)}
    intake, records = by_name["intake"], by_name["records"]
    assert max(intake.started_at, records.started_at) < min(intake.ended_at, records.ended_at)
    assert (await states(committed, request_id))[:2] == [State.EXTRACTING, State.CHECKING]


@spec("booking-orchestration", "Extraction runs intake and records concurrently")
async def test_request_without_a_certificate(committed, submit, process):
    request_id = await submit(certificate=None)
    model = FakeModel()

    await process(request_id, model)

    records = (await saved(committed, request_id))[Step.RECORDS]
    assert records["skipped"] == NO_CERTIFICATE
    assert model.calls == {"intake": 1, "records": 0}
    assert State.CHECKING in await states(committed, request_id)


# --- Each step is saved with its state change ------------------------------------------


@spec("booking-orchestration", "Each step is saved with its state change")
async def test_results_and_state_change_land_together(committed, submit, process, monkeypatch):
    request_id = await submit()
    real_transition = orchestrator.transition

    async def broken_transition(session, request, target, actor, **kw):
        entry = await real_transition(session, request, target, actor, **kw)
        if target == State.CHECKING:
            raise RuntimeError("database went away mid-commit")
        return entry

    monkeypatch.setattr(orchestrator, "transition", broken_transition)
    with pytest.raises(RuntimeError, match="went away"):
        await process(request_id, FakeModel())

    async with committed() as s:
        request = await s.get(BookingRequest, request_id)
    assert request.status == State.EXTRACTING
    assert await saved(committed, request_id) == {}


# --- Checks combine every source -------------------------------------------------------


@spec("booking-orchestration", "Checks combine every source")
async def test_extracted_records_complete_what_is_on_file(committed, submit, process):
    request_id = await submit()

    await process(request_id, FakeModel())

    compliance = (await saved(committed, request_id))[Step.CHECKS]["compliance"]
    assert compliance["outcome"] == "compliant"
    assert {"vaccine": "bordetella", "status": "ok"} in compliance["checks"]
    assert (compliance["records_on_file"], compliance["records_from_certificate"]) == (2, 1)


@spec("booking-orchestration", "Checks combine every source")
async def test_certificate_for_another_pet(committed, submit, process):
    request_id = await submit()

    state = await process(request_id, FakeModel(records=CERTIFICATE | {"pet_name": "Max"}))

    results = await saved(committed, request_id)
    mismatch = results[Step.CHECKS]["pet"]["mismatch"]
    assert mismatch == "certificate names 'Max', booking is for 'Biscuit'"
    assert state == State.RESOLVING
    assert mismatch in results[Step.ROUTE]["reasons"]


@spec("booking-orchestration", "Checks combine every source")
async def test_no_kennel_needed_for_grooming(committed, submit, process):
    request_id = await submit()
    grooming = INTENT | {"service": "grooming", "end_date": START.isoformat()}

    state = await process(request_id, FakeModel(intake=grooming))

    checks = (await saved(committed, request_id))[Step.CHECKS]
    assert checks["capacity"]["status"] == "not_needed"
    assert "capacity" not in {s.name for s in await spans_of(committed, request_id)}
    assert state == State.DRAFTING


# --- Routing is decided by code with reasons -------------------------------------------


@spec("booking-orchestration", "Routing is decided by code with reasons")
async def test_everything_clear_goes_to_drafting(committed, submit, process):
    request_id = await submit()

    state = await process(request_id, FakeModel())

    results = await saved(committed, request_id)
    assert state == State.DRAFTING
    assert results[Step.ROUTE] == {"target": "drafting", "reasons": []}
    assert results[Step.CHECKS]["capacity"] == {
        "status": "found",
        "size_class": "medium",
        "kennel": "M1",
    }


@spec("booking-orchestration", "Routing is decided by code with reasons")
async def test_several_problems_are_all_listed(committed, desk, submit, process):
    async with committed() as s:
        s.add(
            Reservation(
                kennel_id=desk.kennel_id,
                pet_id=desk.olive_id,
                start_date=date(2027, 3, 9),
                end_date=date(2027, 3, 12),
            )
        )
        await s.commit()
    request_id = await submit()
    expiring = CERTIFICATE | {"records": [BORDETELLA | {"expires_on": "2027-03-12"}]}

    state = await process(request_id, FakeModel(records=expiring))

    reasons = (await saved(committed, request_id))[Step.ROUTE]["reasons"]
    assert state == State.RESOLVING
    assert reasons == [
        "vaccine bordetella: expires_during_stay",
        "capacity: no free medium kennel for the stay",
    ]


@spec("booking-orchestration", "Routing is decided by code with reasons")
async def test_no_pet_matched(committed, submit, process):
    request_id = await submit()

    state = await process(request_id, FakeModel(intake=INTENT | {"pet_name": "Rex"}))

    results = await saved(committed, request_id)
    assert state == State.RESOLVING
    assert (results[Step.CHECKS]["compliance"], results[Step.CHECKS]["capacity"]) == (None, None)
    assert PET_UNKNOWN in results[Step.ROUTE]["reasons"]
    assert "compliance" not in {s.name for s in await spans_of(committed, request_id)}


@spec("booking-orchestration", "Routing is decided by code with reasons")
async def test_no_certificate_but_records_on_file_cover_the_stay(committed, submit, process):
    request_id = await submit(certificate=None)
    grooming = INTENT | {"service": "grooming", "end_date": START.isoformat()}

    state = await process(request_id, FakeModel(intake=grooming))

    assert state == State.DRAFTING


@spec("booking-orchestration", "Routing is decided by code with reasons")
async def test_the_matched_pet_is_saved_on_the_request(committed, desk, submit, process):
    request_id = await submit()

    await process(request_id, FakeModel())

    async with committed() as s:
        assert (await s.get(BookingRequest, request_id)).pet_id == desk.biscuit_id


# --- Each run is traced and linked to its request --------------------------------------


@spec("booking-orchestration", "Each run is traced and linked to its request")
async def test_traced_run(committed, submit, process):
    request_id = await submit()

    await process(request_id, FakeModel())

    spans = await spans_of(committed, request_id)
    by_name = {s.name: s for s in spans}
    roots = {s.name for s in spans if s.parent_span_id is None}
    assert roots == {"extract", "check", "route"}
    assert by_name["intake"].parent_span_id == by_name["extract"].id
    assert by_name["records"].parent_span_id == by_name["extract"].id
    assert {by_name["compliance"].parent_span_id, by_name["capacity"].parent_span_id} == {
        by_name["check"].id
    }
    assert sum(s.cost_usd or Decimal(0) for s in spans) > 0
    assert len({s.trace_id for s in spans}) == 1


# --- A crashed run resumes without repeating finished work -----------------------------


class Crash(BaseException):
    """Stands in for a killed process: a BaseException skips every `except Exception`."""


def crash_after(state):
    def hook(finished):
        if finished == state:
            raise Crash(f"killed after {state}")

    return hook


async def trace_count(committed, request_id) -> int:
    async with committed() as s:
        rows = await s.scalars(select(Trace.id).where(Trace.booking_request_id == request_id))
        return len(list(rows))


@spec("booking-orchestration", "A crashed run resumes without repeating finished work")
async def test_crash_after_extraction_resumes_without_model_calls(committed, submit, process):
    request_id = await submit()
    with pytest.raises(Crash):
        await process(request_id, FakeModel(), crash_after=crash_after(State.EXTRACTING))
    assert set(await saved(committed, request_id)) == {Step.INTAKE, Step.RECORDS}

    second = FakeModel()
    state = await process(request_id, second)

    assert state == State.DRAFTING
    assert second.total_calls == 0
    assert set(await saved(committed, request_id)) == set(Step)


@spec("booking-orchestration", "A crashed run resumes without repeating finished work")
async def test_crash_during_extraction_repeats_only_extraction(committed, submit, process):
    request_id = await submit()
    with pytest.raises(Crash):
        await process(request_id, FakeModel(), crash_after=crash_after(State.RECEIVED))
    assert await saved(committed, request_id) == {}

    second = FakeModel()
    state = await process(request_id, second)

    async with committed() as s:
        steps = list(
            await s.scalars(
                select(BookingStepResult.step).where(
                    BookingStepResult.booking_request_id == request_id
                )
            )
        )
    assert state == State.DRAFTING
    assert second.calls == {"intake": 1, "records": 1}
    assert sorted(steps) == sorted(Step)  # exactly one result per step
    assert await states(committed, request_id) == [
        State.EXTRACTING,
        State.CHECKING,
        State.DRAFTING,
    ]


@spec("booking-orchestration", "A crashed run resumes without repeating finished work")
async def test_finished_request_is_left_alone(committed, submit, process):
    request_id = await submit()
    await process(request_id, FakeModel())
    before = (await states(committed, request_id), await trace_count(committed, request_id))

    again = FakeModel()
    state = await process(request_id, again)

    assert state == State.DRAFTING
    assert again.total_calls == 0
    assert (await states(committed, request_id), await trace_count(committed, request_id)) == (
        before
    )


# --- Step failures are recorded and retried --------------------------------------------


async def request_row(committed, request_id) -> BookingRequest:
    async with committed() as s:
        return await s.get(BookingRequest, request_id)


@spec("booking-orchestration", "Step failures are recorded and retried")
async def test_model_unavailable_during_extraction(committed, submit, process):
    request_id = await submit()
    model = FakeModel(intake=503)

    state = await process(request_id, model)

    request = await request_row(committed, request_id)
    assert state == request.status == State.FAILED
    assert request.failed_step == State.EXTRACTING
    assert request.last_error.startswith("intake: LLMError:")
    assert model.calls == {"intake": 2, "records": 1}  # records still ran to completion
    assert await saved(committed, request_id) == {}
    spans = await spans_of(committed, request_id)
    assert all(s.status != "running" for s in spans)
    assert {s.name: s.status for s in spans}["extract"] == "error"


@spec("booking-orchestration", "Step failures are recorded and retried")
async def test_both_failures_are_recorded(committed, submit, process):
    request_id = await submit()

    await process(request_id, FakeModel(intake=503, records=401))

    error = (await request_row(committed, request_id)).last_error
    assert "intake: LLMError" in error and "records: LLMError" in error


@spec("booking-orchestration", "Step failures are recorded and retried")
async def test_output_still_invalid_after_repair_fails_the_step(committed, submit, process):
    request_id = await submit()

    await process(request_id, FakeModel(intake={"approved": True}))

    request = await request_row(committed, request_id)
    assert (request.status, request.failed_step) == (State.FAILED, State.EXTRACTING)
    assert "IntakeInvalidOutput" in request.last_error


@spec("booking-orchestration", "Step failures are recorded and retried")
async def test_retry_after_failure(committed, submit, process):
    request_id = await submit()
    await process(request_id, FakeModel(intake=503))

    state = await process(request_id, FakeModel())

    request = await request_row(committed, request_id)
    assert state == State.DRAFTING
    assert (request.failed_step, request.last_error) == (None, None)
    assert await states(committed, request_id) == [
        State.EXTRACTING,
        State.FAILED,
        State.EXTRACTING,
        State.CHECKING,
        State.DRAFTING,
    ]


@spec("booking-orchestration", "Step failures are recorded and retried")
async def test_a_bug_is_not_hidden_as_a_failed_step(committed, submit, process, monkeypatch):
    request_id = await submit()

    async def broken(*args, **kwargs):
        raise KeyError("bug in the records step")

    monkeypatch.setattr(orchestrator, "run_records", broken)
    with pytest.raises(KeyError):
        await process(request_id, FakeModel())

    assert (await request_row(committed, request_id)).status == State.EXTRACTING


# --- Abandoned spans are closed (run-tracing) -------------------------------------------


@spec("run-tracing", "Abandoned spans are closed")
async def test_span_left_running_by_a_killed_run_is_closed(committed, submit, process):
    request_id = await submit()
    async with committed() as s:
        killed = Trace(name="process booking", booking_request_id=request_id)
        s.add(killed)
        await s.flush()
        stuck = Span(trace_id=killed.id, kind="llm", name="records.extract", status="running")
        s.add(stuck)
        await s.commit()

    await process(request_id, FakeModel())

    async with committed() as s:
        stuck = await s.get(Span, stuck.id)
        killed = await s.get(Trace, killed.id)
    assert stuck.status == "error"
    assert stuck.error == "abandoned: the process stopped before this work finished"
    assert stuck.ended_at is not None
    assert killed.ended_at is not None


@spec("run-tracing", "Abandoned spans are closed")
async def test_finished_spans_are_left_untouched(committed, submit, process):
    request_id = await submit()
    with pytest.raises(Crash):
        await process(request_id, FakeModel(), crash_after=crash_after(State.EXTRACTING))
    before = {s.id: (s.status, s.ended_at, s.error) for s in await spans_of(committed, request_id)}

    await process(request_id, FakeModel())

    after = {s.id: (s.status, s.ended_at, s.error) for s in await spans_of(committed, request_id)}
    assert {i: after[i] for i in before} == before
    assert all(status == "ok" for status, _, _ in before.values())
