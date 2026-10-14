"""Spec: booking-lifecycle, the pure guard (design D6).

The expected rules below are written out independently from the spec, not imported from
app.lifecycle, so these tests check the implementation instead of restating it.
"""

import itertools

import pytest

from app.lifecycle import Actor, IllegalTransition, State, check_transition

spec = pytest.mark.spec
S, A = State, Actor

# Every (from, to, actor) the spec allows, other than leaving FAILED.
ALLOWED = {
    # The system drives processing steps
    (S.RECEIVED, S.EXTRACTING, A.SYSTEM),
    (S.EXTRACTING, S.CHECKING, A.SYSTEM),
    (S.CHECKING, S.RESOLVING, A.SYSTEM),
    (S.CHECKING, S.DRAFTING, A.SYSTEM),
    (S.RESOLVING, S.DRAFTING, A.SYSTEM),
    (S.DRAFTING, S.NEEDS_REVIEW, A.SYSTEM),
    (S.DRAFTING, S.READY, A.SYSTEM),
    # Decisions lead to approved or rejected
    (S.READY, S.APPROVED, A.SYSTEM),
    (S.READY, S.REJECTED, A.STAFF),
    (S.NEEDS_REVIEW, S.APPROVED, A.STAFF),
    (S.NEEDS_REVIEW, S.REJECTED, A.STAFF),
    # Decided requests are sent by the system
    (S.APPROVED, S.SENT, A.SYSTEM),
    (S.REJECTED, S.SENT, A.SYSTEM),
}
CAN_FAIL = {S.EXTRACTING, S.CHECKING, S.RESOLVING, S.DRAFTING, S.APPROVED, S.REJECTED}
ALLOWED |= {(state, S.FAILED, A.SYSTEM) for state in CAN_FAIL}


def expected_allowed(current, target, actor, failed_step) -> bool:
    if current == S.FAILED:
        is_retry = failed_step is not None and target == failed_step
        staff_gives_up = target == S.REJECTED and actor == A.STAFF
        return is_retry or staff_gives_up
    return (current, target, actor) in ALLOWED


def all_cases():
    """Every (from, to, actor) combination, plus every possible failed step for FAILED."""
    for current, target, actor in itertools.product(State, State, Actor):
        failed_steps = [None, *sorted(CAN_FAIL)] if current == S.FAILED else [None]
        for failed_step in failed_steps:
            yield current, target, actor, failed_step


CASES = list(all_cases())
ALLOWED_CASES = [c for c in CASES if expected_allowed(*c)]
REJECTED_CASES = [c for c in CASES if not expected_allowed(*c)]


def case_id(case) -> str:
    current, target, actor, failed_step = case
    suffix = f"[failed in {failed_step}]" if failed_step else ""
    return f"{current}->{target} by {actor}{suffix}"


# --- Only listed transitions are allowed (exhaustive) ---------------------------------


@spec("booking-lifecycle", "Only listed transitions are allowed")
@pytest.mark.parametrize("case", ALLOWED_CASES, ids=case_id)
def test_listed_transition_is_allowed(case):
    current, target, actor, failed_step = case

    check_transition(current, target, actor, failed_step)  # must not raise


@spec("booking-lifecycle", "Only listed transitions are allowed")
@pytest.mark.parametrize("case", REJECTED_CASES, ids=case_id)
def test_unlisted_transition_is_rejected_naming_both_states(case):
    current, target, actor, failed_step = case

    with pytest.raises(IllegalTransition) as exc_info:
        check_transition(current, target, actor, failed_step)

    assert str(current) in str(exc_info.value)
    assert str(target) in str(exc_info.value)


@spec("booking-lifecycle", "Only listed transitions are allowed")
def test_skipping_ahead_is_rejected():
    with pytest.raises(IllegalTransition):
        check_transition(S.RECEIVED, S.SENT, A.SYSTEM)


@spec("booking-lifecycle", "Only listed transitions are allowed")
@pytest.mark.parametrize("target", list(State))
@pytest.mark.parametrize("actor", list(Actor))
def test_sent_is_terminal(target, actor):
    with pytest.raises(IllegalTransition):
        check_transition(S.SENT, target, actor)


# --- Named scenarios, for readability on the walkthrough page -------------------------


@spec("booking-lifecycle", "The system drives processing steps")
def test_staff_cannot_drive_processing():
    with pytest.raises(IllegalTransition):
        check_transition(S.RECEIVED, S.EXTRACTING, A.STAFF)


@spec("booking-lifecycle", "Decisions lead to approved or rejected")
def test_system_cannot_reject():
    with pytest.raises(IllegalTransition):
        check_transition(S.NEEDS_REVIEW, S.REJECTED, A.SYSTEM)


@spec("booking-lifecycle", "Decided requests are sent by the system")
@pytest.mark.parametrize("decided", [S.APPROVED, S.REJECTED])
def test_system_sends_decided_requests(decided):
    check_transition(decided, S.SENT, A.SYSTEM)


@spec("booking-lifecycle", "Decided requests are sent by the system")
@pytest.mark.parametrize("decided", [S.APPROVED, S.REJECTED])
def test_staff_cannot_send(decided):
    with pytest.raises(IllegalTransition):
        check_transition(decided, S.SENT, A.STAFF)


@spec("booking-lifecycle", "Decided requests are sent by the system")
@pytest.mark.parametrize("undecided", [S.READY, S.NEEDS_REVIEW, S.DRAFTING])
def test_undecided_requests_cannot_be_sent(undecided):
    with pytest.raises(IllegalTransition):
        check_transition(undecided, S.SENT, A.SYSTEM)


@spec("booking-lifecycle", "Approval requires deterministic clearance or a person")
def test_only_two_paths_lead_into_approved_plus_the_retry_exception():
    paths_into_approved = {
        (current, actor, failed_step)
        for current, target, actor, failed_step in ALLOWED_CASES
        if target == S.APPROVED
    }

    assert paths_into_approved == {
        (S.READY, A.SYSTEM, None),
        (S.NEEDS_REVIEW, A.STAFF, None),
        # Retry exception: only a request that failed *while already approved*.
        (S.FAILED, A.SYSTEM, S.APPROVED),
        (S.FAILED, A.STAFF, S.APPROVED),
    }


@spec("booking-lifecycle", "Approval requires deterministic clearance or a person")
@pytest.mark.parametrize("actor", list(Actor))
def test_retry_cannot_reach_approved_from_an_earlier_step(actor):
    with pytest.raises(IllegalTransition):
        check_transition(S.FAILED, S.APPROVED, actor, failed_step=S.DRAFTING)


@spec("booking-lifecycle", "Approval requires deterministic clearance or a person")
@pytest.mark.parametrize("current", [S.DRAFTING, S.CHECKING])
@pytest.mark.parametrize("actor", list(Actor))
def test_approval_cannot_skip_the_checks(current, actor):
    with pytest.raises(IllegalTransition):
        check_transition(current, S.APPROVED, actor)


@spec("booking-lifecycle", "Approval requires deterministic clearance or a person")
def test_system_cannot_approve_a_flagged_request():
    with pytest.raises(IllegalTransition):
        check_transition(S.NEEDS_REVIEW, S.APPROVED, A.SYSTEM)


@spec("booking-lifecycle", "Failures record the failed step and the error")
@pytest.mark.parametrize("actor", list(Actor))
def test_retry_returns_to_the_failed_step(actor):
    check_transition(S.FAILED, S.EXTRACTING, actor, failed_step=S.EXTRACTING)


@spec("booking-lifecycle", "Failures record the failed step and the error")
def test_retry_to_a_different_step_is_rejected():
    with pytest.raises(IllegalTransition):
        check_transition(S.FAILED, S.DRAFTING, A.SYSTEM, failed_step=S.EXTRACTING)


@spec("booking-lifecycle", "Failures record the failed step and the error")
def test_failed_without_a_recorded_step_cannot_retry():
    with pytest.raises(IllegalTransition):
        check_transition(S.FAILED, S.EXTRACTING, A.SYSTEM, failed_step=None)


@spec("booking-lifecycle", "Failures record the failed step and the error")
def test_staff_can_give_up_on_a_failed_request():
    check_transition(S.FAILED, S.REJECTED, A.STAFF, failed_step=S.EXTRACTING)
