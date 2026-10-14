"""Spec: vaccine-compliance, the pure check. A Mar 6–9 stay unless stated otherwise."""

from datetime import date

import pytest

from app.compliance import Outcome, VaccineEvidence, VaccineStatus, check
from app.enums import Vaccine

spec = pytest.mark.spec
S = VaccineStatus
RABIES, BORDETELLA, FVRCP, DHPP, LEPTO = (
    Vaccine.RABIES,
    Vaccine.BORDETELLA,
    Vaccine.FVRCP,
    Vaccine.DHPP,
    Vaccine.LEPTOSPIROSIS,
)
START, END = date(2027, 3, 6), date(2027, 3, 9)
JAN_1 = date(2027, 1, 1)


def rec(vaccine, given=JAN_1, expires=None):
    return VaccineEvidence(vaccine=vaccine, administered_on=given, expires_on=expires)


def status_of(vaccine, records, start=START, end=END):
    result = check({vaccine}, records, start, end)
    assert [c.vaccine for c in result.checks] == [vaccine]
    return result.checks[0].status


# --- A vaccine must cover every day the pet is on site --------------------------------


@spec("vaccine-compliance", "A vaccine must cover every day the pet is on site")
@pytest.mark.parametrize(
    ("expires", "expected"),
    [
        (date(2027, 3, 5), S.EXPIRED),  # day before check-in
        (date(2027, 3, 6), S.EXPIRES_DURING_STAY),  # check-in day
        (date(2027, 3, 8), S.EXPIRES_DURING_STAY),  # day before checkout: covers nights only
        (date(2027, 3, 9), S.OK),  # checkout day: the boundary
        (date(2027, 3, 10), S.OK),  # day after checkout
    ],
    ids=["mar5", "mar6", "mar8", "mar9", "mar10"],
)
def test_expiry_boundaries(expires, expected):
    assert status_of(RABIES, [rec(RABIES, expires=expires)]) == expected


@spec("vaccine-compliance", "A vaccine must cover every day the pet is on site")
@pytest.mark.parametrize(
    ("given", "expected"),
    [(date(2027, 3, 6), S.OK), (date(2027, 3, 7), S.NOT_YET_GIVEN)],
    ids=["given-on-check-in", "given-after-check-in"],
)
def test_administration_boundaries(given, expected):
    assert status_of(RABIES, [rec(RABIES, given=given, expires=date(2028, 1, 1))]) == expected


@spec("vaccine-compliance", "A vaccine must cover every day the pet is on site")
def test_day_service_on_the_expiry_date():
    day = date(2027, 3, 6)

    status = status_of(BORDETELLA, [rec(BORDETELLA, expires=day)], start=day, end=day)

    assert status == S.OK


# --- Any covering record satisfies the vaccine ----------------------------------------


@spec("vaccine-compliance", "Any covering record satisfies the vaccine")
def test_booster_replaces_an_expired_shot():
    records = [rec(RABIES, expires=date(2026, 6, 1)), rec(RABIES, expires=date(2028, 1, 1))]

    assert status_of(RABIES, records) == S.OK


@spec("vaccine-compliance", "Any covering record satisfies the vaccine")
def test_known_expiry_outweighs_an_unknown_one():
    records = [rec(RABIES, expires=None), rec(RABIES, expires=date(2028, 1, 1))]

    assert status_of(RABIES, records) == S.OK


@spec("vaccine-compliance", "Any covering record satisfies the vaccine")
def test_record_order_does_not_matter():
    records = [rec(RABIES, expires=date(2028, 1, 1)), rec(RABIES, expires=date(2026, 6, 1))]

    assert status_of(RABIES, records) == status_of(RABIES, list(reversed(records))) == S.OK


# --- Uncovered vaccines get the most useful explanation -------------------------------


@spec("vaccine-compliance", "Uncovered vaccines get the most useful explanation")
def test_no_records_at_all_is_missing():
    assert status_of(BORDETELLA, []) == S.MISSING


@spec("vaccine-compliance", "Uncovered vaccines get the most useful explanation")
def test_unknown_expiry_with_nothing_better():
    assert status_of(FVRCP, [rec(FVRCP, expires=None)]) == S.UNKNOWN_EXPIRY


@spec("vaccine-compliance", "Uncovered vaccines get the most useful explanation")
def test_mid_stay_expiry_beats_an_older_expired_record():
    records = [rec(RABIES, expires=date(2026, 6, 1)), rec(RABIES, expires=date(2027, 3, 7))]

    assert status_of(RABIES, records) == S.EXPIRES_DURING_STAY


@spec("vaccine-compliance", "Uncovered vaccines get the most useful explanation")
@pytest.mark.parametrize(
    ("records", "expected"),
    [
        # unknown_expiry outranks expires_during_stay, not_yet_given, and expired
        (
            [
                rec(RABIES, expires=None),
                rec(RABIES, expires=date(2027, 3, 7)),
                rec(RABIES, given=date(2027, 3, 8), expires=date(2028, 1, 1)),
                rec(RABIES, expires=date(2026, 6, 1)),
            ],
            S.UNKNOWN_EXPIRY,
        ),
        # expires_during_stay outranks not_yet_given and expired
        (
            [
                rec(RABIES, expires=date(2027, 3, 7)),
                rec(RABIES, given=date(2027, 3, 8), expires=date(2028, 1, 1)),
                rec(RABIES, expires=date(2026, 6, 1)),
            ],
            S.EXPIRES_DURING_STAY,
        ),
        # not_yet_given outranks expired
        (
            [
                rec(RABIES, given=date(2027, 3, 8), expires=date(2028, 1, 1)),
                rec(RABIES, expires=date(2026, 6, 1)),
            ],
            S.NOT_YET_GIVEN,
        ),
        # a record given after check-in with no expiry is not_yet_given, not unknown_expiry
        ([rec(RABIES, given=date(2027, 3, 8), expires=None)], S.NOT_YET_GIVEN),
    ],
    ids=["unknown-first", "mid-stay-second", "not-yet-given-third", "late-unknown"],
)
def test_precedence_order(records, expected):
    assert status_of(RABIES, records) == expected


# --- Outcome separates failures from human review -------------------------------------


@spec("vaccine-compliance", "Outcome separates failures from human review")
def test_everything_covered_is_compliant():
    covered = date(2028, 1, 1)

    result = check(
        {RABIES, DHPP}, [rec(RABIES, expires=covered), rec(DHPP, expires=covered)], START, END
    )

    assert result.outcome == Outcome.COMPLIANT


@spec("vaccine-compliance", "Outcome separates failures from human review")
def test_unknown_expiry_alone_needs_review():
    result = check({RABIES, FVRCP}, [rec(RABIES, expires=date(2028, 1, 1)), rec(FVRCP)], START, END)

    assert result.outcome == Outcome.NEEDS_REVIEW


@spec("vaccine-compliance", "Outcome separates failures from human review")
@pytest.mark.parametrize(
    "failing",
    [
        [],  # missing
        [rec(BORDETELLA, expires=date(2026, 6, 1))],  # expired
        [rec(BORDETELLA, expires=date(2027, 3, 7))],  # expires during stay
        [rec(BORDETELLA, given=date(2027, 3, 8), expires=date(2028, 1, 1))],  # not yet given
    ],
    ids=["missing", "expired", "expires-during-stay", "not-yet-given"],
)
def test_a_definite_failure_outweighs_unknown_expiry(failing):
    result = check({FVRCP, BORDETELLA}, [rec(FVRCP), *failing], START, END)

    assert result.outcome == Outcome.NOT_COMPLIANT


@spec("vaccine-compliance", "Outcome separates failures from human review")
def test_no_rules_for_the_service_is_compliant():
    result = check(set(), [rec(RABIES, expires=date(2020, 1, 1))], START, END)

    assert result == type(result)(outcome=Outcome.COMPLIANT, checks=())


# --- Only required vaccines are judged ------------------------------------------------


@spec("vaccine-compliance", "Only required vaccines are judged")
def test_extra_records_are_ignored():
    records = [rec(RABIES, expires=date(2028, 1, 1)), rec(LEPTO, expires=date(2020, 1, 1))]

    result = check({RABIES}, records, START, END)

    assert [(c.vaccine, c.status) for c in result.checks] == [(RABIES, S.OK)]
    assert result.outcome == Outcome.COMPLIANT


@spec("vaccine-compliance", "Only required vaccines are judged")
def test_one_entry_per_required_vaccine_in_stable_order():
    result = check([RABIES, DHPP, BORDETELLA, RABIES], [], START, END)

    assert [c.vaccine for c in result.checks] == sorted({RABIES, DHPP, BORDETELLA})


# --- Invalid stays are rejected -------------------------------------------------------


@spec("vaccine-compliance", "Invalid stays are rejected")
def test_end_before_start_is_rejected():
    with pytest.raises(ValueError, match="end"):
        check({RABIES}, [], date(2027, 3, 9), date(2027, 3, 6))
