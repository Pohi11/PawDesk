"""The only way a booking request changes state (spec: booking-lifecycle, design D6/D7).

transition() checks the guard, applies the change, and appends the log row in a single
flush. The caller owns the commit, so a step's output, its state change, and its log row
land in one transaction or not at all.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from app.lifecycle import Actor, State, check_transition
from app.models import BookingRequest, BookingTransition


class TransitionConflict(Exception):
    """Someone else changed the request after it was loaded; reload and decide again."""


async def transition(
    session: AsyncSession,
    request: BookingRequest,
    target: State,
    actor: Actor,
    *,
    reason: str | None = None,
    error: str | None = None,
) -> BookingTransition:
    # Read these now: if the flush below fails, SQLAlchemy expires `request`, and touching
    # its attributes afterward would try to reload it from a session that is rolled back.
    request_id, current = request.id, request.status

    # Guard first, before touching anything: an illegal transition changes nothing.
    check_transition(current, target, actor, request.failed_step)

    if target == State.FAILED:
        if not error:
            raise ValueError("moving a request to failed requires an error message")
        request.failed_step = current
        request.last_error = error
    elif current == State.FAILED:
        # Leaving FAILED (retry or staff rejection) clears the recorded failure.
        request.failed_step = None
        request.last_error = None

    request.status = target
    entry = BookingTransition(
        booking_request_id=request_id,
        from_status=current,
        to_status=target,
        actor=actor,
        reason=reason,
    )
    session.add(entry)

    try:
        # The UPDATE carries `WHERE version = <loaded version>`. If another session already
        # moved this request, it matches no row and SQLAlchemy raises StaleDataError. The
        # caller must roll back, which also discards the log row added above.
        await session.flush()
    except StaleDataError as exc:
        raise TransitionConflict(
            f"booking request {request_id} changed since it was loaded (was {current})"
        ) from exc

    return entry
