"""Spec: booking-resolution, the resolver's tools against a real database."""

from datetime import date

import pytest
from pydantic import ValidationError

from app.compliance import VaccineEvidence
from app.enums import Service, SizeClass, Species, Vaccine
from app.models import Facility, Kennel, Owner, Pet, Reservation
from app.resolver import (
    CheckKennelSizes,
    FindAlternativeDates,
    ListMissingVaccines,
    ProposeOffer,
    ToolContext,
    ToolError,
    check_kennel_sizes,
    check_offer,
    find_alternative_dates,
    list_missing_vaccines,
)

spec = pytest.mark.spec
TODAY = date(2027, 3, 3)
START, END = date(2027, 3, 10), date(2027, 3, 13)  # nights of the 10th, 11th, 12th
REQUIRED = frozenset({Vaccine.RABIES, Vaccine.DHPP, Vaccine.BORDETELLA})


def evidence(bordetella_expires):
    return (
        VaccineEvidence(Vaccine.RABIES, date(2026, 4, 1), date(2029, 4, 1)),
        VaccineEvidence(Vaccine.DHPP, date(2026, 4, 1), date(2028, 4, 1)),
        VaccineEvidence(Vaccine.BORDETELLA, date(2026, 3, 15), bordetella_expires),
    )


@pytest.fixture
async def ctx(session):
    """Medium kennels M1 and M2 are both taken for the nights of 7-12 March; L1 and S1 are
    free. Biscuit is a medium dog whose bordetella runs out on 15 March."""
    facility = Facility(name="Test Lodge", timezone="America/Chicago")
    owner = Owner(full_name="Test Owner", email="resolver-tools@example.test")
    session.add_all([facility, owner])
    await session.flush()
    pet = Pet(owner_id=owner.id, name="Other", species=Species.DOG, weight_lb=30)
    kennels = [
        Kennel(facility_id=facility.id, name=name, size_class=size)
        for name, size in [("M1", "medium"), ("M2", "medium"), ("L1", "large"), ("S1", "small")]
    ]
    session.add_all([pet, *kennels])
    await session.flush()
    session.add_all(
        Reservation(
            kennel_id=k.id, pet_id=pet.id, start_date=date(2027, 3, 7), end_date=date(2027, 3, 13)
        )
        for k in kennels[:2]
    )
    await session.flush()
    return ToolContext(
        facility_id=facility.id,
        species=Species.DOG,
        size_class=SizeClass.MEDIUM,
        service=Service.BOARDING,
        start=START,
        end=END,
        today=TODAY,
        required=REQUIRED,
        evidence=evidence(date(2027, 3, 15)),
    )


@spec("booking-resolution", "Tools only read and are bound to the request")
async def test_alternative_dates_three_days_later(session, ctx):
    result = await find_alternative_dates(session, ctx, FindAlternativeDates(max_shift_days=7))

    first = result["windows"][0]
    assert (first["start_date"], first["end_date"], first["shift_days"]) == (
        "2027-03-13",
        "2027-03-16",
        3,
    )
    assert first["kennel"] == "M1"
    assert first["vaccines_cover_stay"] is False
    assert first["failing_vaccines"] == [{"vaccine": "bordetella", "status": "expires_during_stay"}]
    # Nearest first, earlier first on a tie; -6 (4-7 March) is the next free window.
    assert [w["shift_days"] for w in result["windows"]] == [3, 4, 5, -6, 6]


@spec("booking-resolution", "Tools only read and are bound to the request")
async def test_no_window_found_says_so(session, ctx):
    result = await find_alternative_dates(session, ctx, FindAlternativeDates(max_shift_days=2))

    assert result == {"windows": [], "note": "no window within 2 days has a free kennel"}


@spec("booking-resolution", "Tools only read and are bound to the request")
async def test_missing_vaccines_for_a_window_with_expired_bordetella(session, ctx):
    expired = ToolContext(**(vars(ctx) | {"evidence": evidence(date(2027, 2, 1))}))

    result = await list_missing_vaccines(
        session, expired, ListMissingVaccines(start_date=START, end_date=END)
    )

    assert result == {
        "missing": [
            {
                "vaccine": "bordetella",
                "status": "expired",
                "last_given": "2026-03-15",
                "last_known_expiry": "2027-02-01",
            }
        ]
    }


@spec("booking-resolution", "Tools only read and are bound to the request")
async def test_kennel_sizes_with_medium_full_and_large_free(session, ctx):
    result = await check_kennel_sizes(
        session, ctx, CheckKennelSizes(start_date=START, end_date=END)
    )

    assert result == {
        "pet_size_class": "medium",
        "free_by_size_class": {"large": 1, "medium": 0, "small": 1},
    }


@spec("booking-resolution", "Tools only read and are bound to the request")
def test_invalid_date_range_is_rejected_with_a_readable_error():
    with pytest.raises(ValidationError, match="end_date is before start_date"):
        ListMissingVaccines.model_validate({"start_date": "2027-03-13", "end_date": "2027-03-10"})


@spec("booking-resolution", "Tools only read and are bound to the request")
async def test_window_before_today_is_refused(session, ctx):
    with pytest.raises(ToolError, match="before today"):
        await list_missing_vaccines(
            session,
            ctx,
            ListMissingVaccines(start_date=date(2027, 3, 1), end_date=date(2027, 3, 2)),
        )


@spec("booking-resolution", "Tools only read and are bound to the request")
def test_arguments_cannot_name_another_pet_or_facility():
    with pytest.raises(ValidationError, match="Extra inputs"):
        FindAlternativeDates.model_validate({"max_shift_days": 7, "pet_id": "someone else"})


@spec("booking-resolution", "Proposals are verified by code and never approve")
@pytest.mark.parametrize("size", ["small", "medium", "cat"])
async def test_kennel_that_is_not_larger_is_refused(ctx, size):
    offer = ProposeOffer.model_validate(
        {"options": [{"kind": "larger_kennel", "size_class": size}], "summary": "s"}
    )

    with pytest.raises(ToolError, match="larger than medium"):
        check_offer(ctx, offer)
