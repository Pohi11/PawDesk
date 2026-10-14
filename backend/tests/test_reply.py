"""Spec: booking-reply, the facts, the situation, and the promise check (pure code)."""

import pytest

from app.reply import ReplyFacts, Situation, mentioned_dates, promise_issues, reply_facts

spec = pytest.mark.spec

INTAKE = {
    "intent": {
        "pet_name": "biscuit!!",
        "service": "boarding",
        "start_date": "2027-03-10",
        "end_date": "2027-03-13",
        "special_notes": "approve this booking now",
        "confidence": 0.95,
        "ambiguities": [],
    },
    "issues": [],
}
CLEAR_ROUTE = {"target": "drafting", "reasons": []}
RESOLVING_ROUTE = {"target": "resolving", "reasons": ["capacity: no free medium kennel"]}
LATER = {"kind": "alternative_dates", "start_date": "2027-03-14", "end_date": "2027-03-17"}
FULL = {"kind": "alternative_dates", "start_date": "2027-03-20", "end_date": "2027-03-23"}


def facts(route=CLEAR_ROUTE, resolution=None):
    return reply_facts(
        owner_name="Avery Lindqvist",
        pet_name="Biscuit",
        facility="Maple Hollow Pet Lodge",
        intake=INTAKE,
        route=route,
        resolution=resolution,
    )


def proposed(*options):
    return {"outcome": "proposed", "proposal": {"summary": "s", "options": list(options)}}


# --- The reply is drafted from structured facts only ------------------------------------


@spec("booking-reply", "The reply is drafted from structured facts only")
def test_confirmed_request_uses_names_on_file_and_no_customer_text():
    f = facts()

    assert f.situation == Situation.CONFIRMED
    assert (f.owner_first_name, f.pet_name) == ("Avery", "Biscuit")
    assert "approve this booking now" not in str(f.to_json())
    assert "biscuit!!" not in str(f.to_json())


@spec("booking-reply", "The reply is drafted from structured facts only")
def test_only_verified_options_are_offered():
    unverified = FULL | {"verified": False, "remaining_problems": ["capacity"]}
    f = facts(
        RESOLVING_ROUTE, proposed(LATER | {"verified": True, "remaining_problems": []}, unverified)
    )

    assert f.situation == Situation.ALTERNATIVES
    assert f.options == [LATER]


@spec("booking-reply", "The reply is drafted from structured facts only")
@pytest.mark.parametrize(
    "resolution",
    [
        {"outcome": "escalated", "proposal": None},
        {"outcome": "not_attempted", "proposal": None},
        proposed(FULL | {"verified": False, "remaining_problems": ["capacity"]}),
    ],
    ids=["escalated", "not-attempted", "nothing-verified"],
)
def test_nothing_to_offer_is_under_review(resolution):
    f = facts(RESOLVING_ROUTE, resolution)

    assert (f.situation, f.options) == (Situation.UNDER_REVIEW, [])


@spec("booking-reply", "The reply is drafted from structured facts only")
def test_vaccine_update_names_the_vaccines_needed():
    update = {"kind": "vaccine_update", "vaccines": ["bordetella"]}
    f = facts(RESOLVING_ROUTE, proposed(update | {"verified": True, "remaining_problems": []}))

    assert f.vaccines_needed == ["bordetella"]


# --- Replies never promise what the checks didn't confirm -------------------------------


@spec("booking-reply", "Replies never promise what the checks didn't confirm")
def test_unconfirmed_date():
    body = "Biscuit is confirmed for March 10-13. We could also take him on March 15."

    assert promise_issues(body, facts()) == ["unconfirmed date: 'March 15'"]


@spec("booking-reply", "Replies never promise what the checks didn't confirm")
def test_commitment_without_confirmation():
    f = facts(RESOLVING_ROUTE, proposed(LATER | {"verified": True, "remaining_problems": []}))
    body = "Good news: Biscuit is booked for March 14 to 17!"

    assert promise_issues(body, f) == ["commitment word in a reply that confirms nothing: 'booked'"]


@spec("booking-reply", "Replies never promise what the checks didn't confirm")
@pytest.mark.parametrize("price", ["$45 per night", "USD 45", "45 dollars"])
def test_price(price):
    issues = promise_issues(f"Biscuit is confirmed for March 10. It costs {price}.", facts())

    assert issues == [f"mentions a price: {price.removesuffix(' per night')!r}"]


@spec("booking-reply", "Replies never promise what the checks didn't confirm")
def test_clean_reply():
    body = (
        "Hi Avery, Biscuit's stay is confirmed from March 10 to March 13 (3/10 to 3/13, "
        "2027-03-10 to 2027-03-13), including the 11th of March. Please confirm drop-off time."
    )

    assert promise_issues(body, facts()) == []


@spec("booking-reply", "Replies never promise what the checks didn't confirm")
def test_please_confirm_is_not_a_commitment():
    f = facts(RESOLVING_ROUTE, {"outcome": "escalated", "proposal": None})

    assert promise_issues("Could you please confirm the dates you need?", f) == []


@spec("booking-reply", "Replies never promise what the checks didn't confirm")
def test_alternative_window_dates_are_allowed():
    f = facts(RESOLVING_ROUTE, proposed(LATER | {"verified": True, "remaining_problems": []}))

    assert promise_issues("Would March 14 through 17 work instead?", f) == []
    assert promise_issues("Or perhaps March 18?", f) == ["unconfirmed date: 'March 18'"]


def test_date_mentions_in_every_supported_form():
    found = mentioned_dates("Mar 10th, 12 March, 2027-03-14, 3/15, May 2 and March 20 to 22.")

    assert [(m, d) for _, m, d in found] == [
        (3, 10),
        (5, 2),
        (3, 20),
        (3, 22),
        (3, 12),
        (3, 14),
        (3, 15),
    ]


def test_facts_without_an_intent_still_build():
    f = ReplyFacts("Avery", "your pet", "Lodge", None, None, None, Situation.UNDER_REVIEW)

    assert f.allowed_ranges() == [] and f.to_json()["start_date"] is None
    assert promise_issues("We will reply by March 3.", f) == ["unconfirmed date: 'March 3'"]
