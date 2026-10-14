"""Staff decisions on flagged requests (spec: staff-approval; decision record 0011).

A request waiting in `needs_review` is paused durably: nothing runs until a staff action
records an Approval and moves it on, in one transaction. Processing then resumes from the
new state, exactly as it would after a crash.
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.enums import ApprovalAction, Step
from app.lifecycle import Actor, State
from app.models import Approval, BookingRequest, BookingStepResult, Owner, Pet
from app.transitions import transition


class NotWaiting(Exception):
    """The request isn't waiting for review (already decided, or never flagged)."""


async def decide(
    sessions: async_sessionmaker[AsyncSession],
    request_id: uuid.UUID,
    action: ApprovalAction,
    staff_name: str,
    *,
    reason: str | None = None,
    reply: str | None = None,
) -> None:
    """Record the decision and move the request, or change nothing.

    Two staff members acting at once both see `needs_review`; the version check in
    transition() lets the first one win and raises TransitionConflict for the second,
    whose Approval row is rolled back with it.
    """
    async with sessions() as session:
        request = await session.get(BookingRequest, request_id)
        if request is None:
            raise LookupError(f"no booking request {request_id}")
        if request.status != State.NEEDS_REVIEW:
            raise NotWaiting(f"request is {request.status}, not waiting for review")

        session.add(
            Approval(
                booking_request_id=request.id,
                action=action,
                staff_name=staff_name,
                reason=reason,
                edited_reply=reply if action == ApprovalAction.EDIT_AND_APPROVE else None,
            )
        )
        target = State.REJECTED if action == ApprovalAction.REJECT else State.APPROVED
        await transition(session, request, target, Actor.STAFF, reason=reason or str(action))
        await session.commit()


async def review_queue(session: AsyncSession) -> list[dict[str, Any]]:
    """Requests waiting for a person, oldest first, with why they were flagged."""
    rows = await session.execute(
        select(BookingRequest, Owner.full_name, Pet.name)
        .join(Owner, Owner.id == BookingRequest.owner_id)
        .outerjoin(Pet, Pet.id == BookingRequest.pet_id)
        .where(BookingRequest.status == State.NEEDS_REVIEW)
        .order_by(BookingRequest.created_at, BookingRequest.id)
    )
    queue = []
    for request, owner_name, pet_name in rows:
        results = dict(
            (
                await session.execute(
                    select(BookingStepResult.step, BookingStepResult.output).where(
                        BookingStepResult.booking_request_id == request.id,
                        BookingStepResult.step.in_([Step.INTAKE, Step.REPLY]),
                    )
                )
            ).all()
        )
        intent = (results.get(Step.INTAKE) or {}).get("intent") or {}
        reply = results.get(Step.REPLY) or {}
        queue.append(
            {
                "id": str(request.id),
                "created_at": request.created_at.isoformat(),
                "owner": owner_name,
                "pet": pet_name,
                "service": intent.get("service"),
                "start_date": intent.get("start_date"),
                "end_date": intent.get("end_date"),
                "situation": reply.get("situation"),
                "flags": reply.get("flags", []),
                "draft": reply.get("draft"),
            }
        )
    return queue
