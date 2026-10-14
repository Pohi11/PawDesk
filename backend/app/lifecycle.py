"""Booking-request lifecycle rules (spec: booking-lifecycle, design D6).

Pure rules only: no database, no I/O. The transition service (app/transitions.py) calls
check_transition() before changing any state.
"""

from enum import StrEnum


class State(StrEnum):
    RECEIVED = "received"
    EXTRACTING = "extracting"
    CHECKING = "checking"
    RESOLVING = "resolving"
    DRAFTING = "drafting"
    NEEDS_REVIEW = "needs_review"
    READY = "ready"
    APPROVED = "approved"
    REJECTED = "rejected"
    SENT = "sent"
    FAILED = "failed"


class Actor(StrEnum):
    SYSTEM = "system"
    STAFF = "staff"


class IllegalTransition(Exception):
    """Raised when a (from, to, actor) combination is not allowed."""


S, A = State, Actor

# States a request can fail in: the steps that do real work, plus sending a decided reply.
CAN_FAIL = frozenset({S.EXTRACTING, S.CHECKING, S.RESOLVING, S.DRAFTING, S.APPROVED, S.REJECTED})

# Every allowed (from, to, actor), written to read like the spec. Leaving FAILED is the one
# case that depends on more than these three values, so it is handled in code instead.
ALLOWED: frozenset[tuple[State, State, Actor]] = frozenset(
    {
        # The system drives processing steps
        (S.RECEIVED, S.EXTRACTING, A.SYSTEM),
        (S.EXTRACTING, S.CHECKING, A.SYSTEM),
        (S.CHECKING, S.RESOLVING, A.SYSTEM),
        (S.CHECKING, S.DRAFTING, A.SYSTEM),
        (S.RESOLVING, S.DRAFTING, A.SYSTEM),
        (S.DRAFTING, S.NEEDS_REVIEW, A.SYSTEM),
        (S.DRAFTING, S.READY, A.SYSTEM),
        # Decisions: the only ways into APPROVED are system-from-READY and staff-from-NEEDS_REVIEW
        (S.READY, S.APPROVED, A.SYSTEM),
        (S.READY, S.REJECTED, A.STAFF),
        (S.NEEDS_REVIEW, S.APPROVED, A.STAFF),
        (S.NEEDS_REVIEW, S.REJECTED, A.STAFF),
        # Decided requests are sent by the system
        (S.APPROVED, S.SENT, A.SYSTEM),
        (S.REJECTED, S.SENT, A.SYSTEM),
        # Any working step can fail
        *((state, S.FAILED, A.SYSTEM) for state in CAN_FAIL),
    }
)


def check_transition(
    current: State, target: State, actor: Actor, failed_step: State | None = None
) -> None:
    """Return None if `actor` may move a request from `current` to `target`; otherwise raise
    IllegalTransition with a message naming both states.

    `failed_step` is the state a failed request failed in. It only matters when `current`
    is FAILED: a retry may only go back to exactly that state.
    """
    if current == S.FAILED:
        # Checked first: FAILED never appears as a "from" state in ALLOWED.
        is_retry = failed_step is not None and target == failed_step
        staff_gives_up = target == S.REJECTED and actor == A.STAFF
        if is_retry or staff_gives_up:
            return
    elif (current, target, actor) in ALLOWED:
        return

    detail = f" (failed in {failed_step})" if current == S.FAILED else ""
    raise IllegalTransition(f"{actor} may not move a request from {current} to {target}{detail}")
