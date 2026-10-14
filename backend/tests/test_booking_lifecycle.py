"""Spec: booking-lifecycle, the parts stored in Postgres (schema now; transition service later)."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.enums import ApprovalAction
from app.lifecycle import State
from app.models import Approval, BookingRequest, Facility, Owner

spec = pytest.mark.spec


async def make_request(session) -> BookingRequest:
    facility = Facility(name="Test Lodge", timezone="America/Chicago")
    owner = Owner(full_name="Test Owner", email="lifecycle-owner@example.test")
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
