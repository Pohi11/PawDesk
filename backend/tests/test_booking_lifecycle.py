"""Spec: booking-lifecycle, the parts stored in Postgres: schema and the transition service."""

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.db import make_sessionmaker
from app.enums import ApprovalAction
from app.lifecycle import Actor, IllegalTransition, State
from app.models import Approval, BookingRequest, BookingTransition, Facility, Owner
from app.transitions import TransitionConflict, transition

spec = pytest.mark.spec


async def make_request(session, email="lifecycle-owner@example.test") -> BookingRequest:
    facility = Facility(name="Test Lodge", timezone="America/Chicago")
    owner = Owner(full_name="Test Owner", email=email)
    session.add_all([facility, owner])
    await session.flush()
    request = BookingRequest(
        facility_id=facility.id, owner_id=owner.id, raw_message="Can Biscuit board Fri-Mon?"
    )
    session.add(request)
    await session.flush()
    return request


@spec("booking-lifecycle", "Booking requests have exactly one lifecycle state")
async def test_new_request_starts_received(session):
    request = await make_request(session)

    assert request.status == State.RECEIVED
    assert request.version == 1


@spec("booking-lifecycle", "Booking requests have exactly one lifecycle state")
async def test_unknown_state_rejected(session):
    request = await make_request(session)

    with pytest.raises(IntegrityError, match="ck_booking_requests_status"):
        await session.execute(
            text("UPDATE booking_requests SET status = 'pending' WHERE id = :id"),
            {"id": request.id},
        )


@spec("booking-lifecycle", "Failures record the failed step and the error")
@pytest.mark.parametrize(
    ("status", "failed_step"),
    [("failed", None), ("checking", "extracting")],
    ids=["failed-without-step", "step-without-failed"],
)
async def test_failed_step_is_set_exactly_when_failed(session, status, failed_step):
    request = await make_request(session)

    with pytest.raises(IntegrityError, match="ck_booking_requests_failed_step_iff_failed"):
        await session.execute(
            text("UPDATE booking_requests SET status = :s, failed_step = :f WHERE id = :id"),
            {"s": status, "f": failed_step, "id": request.id},
        )


@spec("booking-lifecycle", "Staff decisions are recorded as approvals")
@pytest.mark.parametrize("reason", [None, "", "   "], ids=["null", "empty", "blank"])
async def test_reject_without_a_reason_is_rejected(session, reason):
    request = await make_request(session)
    session.add(
        Approval(
            booking_request_id=request.id,
            action=ApprovalAction.REJECT,
            staff_name="Sam",
            reason=reason,
        )
    )

    with pytest.raises(IntegrityError, match="ck_approvals_reject_requires_reason"):
        await session.flush()


@spec("booking-lifecycle", "Staff decisions are recorded as approvals")
async def test_approve_needs_no_reason(session):
    request = await make_request(session)
    session.add(
        Approval(booking_request_id=request.id, action=ApprovalAction.APPROVE, staff_name="Sam")
    )

    await session.flush()


# --- The transition service -----------------------------------------------------------


async def log_entries(session, request):
    rows = await session.scalars(
        select(BookingTransition)
        .where(BookingTransition.booking_request_id == request.id)
        .order_by(BookingTransition.created_at, BookingTransition.id)
    )
    return list(rows)


async def advance(session, request, *steps):
    for target in steps:
        await transition(session, request, target, Actor.SYSTEM)


@spec("booking-lifecycle", "The system drives processing steps")
async def test_allowed_processing_transition_is_saved(session):
    request = await make_request(session)
    await advance(session, request, State.EXTRACTING, State.CHECKING, State.DRAFTING)

    stored = await session.scalar(
        select(BookingRequest.status).where(BookingRequest.id == request.id)
    )

    assert stored == State.DRAFTING


@spec("booking-lifecycle", "Every transition is logged")
async def test_successful_transition_adds_a_log_entry(session):
    request = await make_request(session)
    await advance(session, request, State.EXTRACTING, State.CHECKING, State.DRAFTING)
    await advance(session, request, State.NEEDS_REVIEW)

    await transition(session, request, State.REJECTED, Actor.STAFF, reason="vaccines expired")

    last = (await log_entries(session, request))[-1]
    assert (last.from_status, last.to_status, last.actor, last.reason) == (
        State.NEEDS_REVIEW,
        State.REJECTED,
        Actor.STAFF,
        "vaccines expired",
    )


@spec("booking-lifecycle", "Every transition is logged")
@spec("booking-lifecycle", "Only listed transitions are allowed")
async def test_rejected_transition_changes_and_logs_nothing(session):
    request = await make_request(session)

    with pytest.raises(IllegalTransition):
        await transition(session, request, State.SENT, Actor.SYSTEM)

    assert request.status == State.RECEIVED
    assert await log_entries(session, request) == []


@spec("booking-lifecycle", "Failures record the failed step and the error")
async def test_failure_is_recorded(session):
    request = await make_request(session)
    await advance(session, request, State.EXTRACTING)

    await transition(session, request, State.FAILED, Actor.SYSTEM, error="model timeout")

    assert (request.status, request.failed_step, request.last_error) == (
        State.FAILED,
        State.EXTRACTING,
        "model timeout",
    )


@spec("booking-lifecycle", "Failures record the failed step and the error")
async def test_failing_without_an_error_message_is_refused(session):
    request = await make_request(session)
    await advance(session, request, State.EXTRACTING)

    with pytest.raises(ValueError, match="error message"):
        await transition(session, request, State.FAILED, Actor.SYSTEM)

    assert request.status == State.EXTRACTING


@spec("booking-lifecycle", "Failures record the failed step and the error")
async def test_retry_returns_to_the_failed_step_and_clears_it(session):
    request = await make_request(session)
    await advance(session, request, State.EXTRACTING)
    await transition(session, request, State.FAILED, Actor.SYSTEM, error="model timeout")

    await transition(session, request, State.EXTRACTING, Actor.SYSTEM)

    assert (request.status, request.failed_step, request.last_error) == (
        State.EXTRACTING,
        None,
        None,
    )


@spec("booking-lifecycle", "Failures record the failed step and the error")
async def test_staff_gives_up_on_a_failed_request(session):
    request = await make_request(session)
    await advance(session, request, State.EXTRACTING)
    await transition(session, request, State.FAILED, Actor.SYSTEM, error="model timeout")

    await transition(session, request, State.REJECTED, Actor.STAFF, reason="unreadable photo")

    assert (request.status, request.failed_step) == (State.REJECTED, None)


@spec("booking-lifecycle", "Concurrent updates do not overwrite each other")
async def test_stale_update_is_rejected(engine):
    """Two real sessions on two connections, so this test commits and cleans up after itself
    instead of using the rolled-back `session` fixture."""
    sessions = make_sessionmaker(engine)
    async with sessions() as setup:
        request = await make_request(setup, email="stale-update@example.test")
        await advance(setup, request, State.EXTRACTING, State.CHECKING, State.DRAFTING)
        await advance(setup, request, State.NEEDS_REVIEW)
        await setup.commit()
        request_id, owner_id, facility_id = request.id, request.owner_id, request.facility_id

    try:
        async with sessions() as a, sessions() as b:
            seen_by_a = await a.get(BookingRequest, request_id)
            seen_by_b = await b.get(BookingRequest, request_id)  # same version as A

            await transition(a, seen_by_a, State.APPROVED, Actor.STAFF)
            await a.commit()

            with pytest.raises(TransitionConflict):
                await transition(b, seen_by_b, State.REJECTED, Actor.STAFF, reason="too late")
            await b.rollback()

        async with sessions() as check:
            final = await check.get(BookingRequest, request_id)
            entries = await log_entries(check, final)
            assert final.status == State.APPROVED
            assert [e.to_status for e in entries][-1] == State.APPROVED
            assert sum(e.to_status in (State.APPROVED, State.REJECTED) for e in entries) == 1
    finally:
        async with sessions() as cleanup:
            for table, column, value in [
                ("booking_transitions", "booking_request_id", request_id),
                ("booking_requests", "id", request_id),
                ("owners", "id", owner_id),
                ("facilities", "id", facility_id),
            ]:
                await cleanup.execute(
                    text(f"DELETE FROM {table} WHERE {column} = :v"), {"v": value}
                )
            await cleanup.commit()
