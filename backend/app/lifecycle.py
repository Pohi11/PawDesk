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


def check_transition(
    current: State, target: State, actor: Actor, failed_step: State | None = None
) -> None:
    """Return None if `actor` may move a request from `current` to `target`; otherwise raise
    IllegalTransition with a message naming both states.

    `failed_step` is the state a failed request failed in. It only matters when `current`
    is FAILED: a retry may only go back to exactly that state.
    """
    raise NotImplementedError
