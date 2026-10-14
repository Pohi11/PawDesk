"""Spec: kennel-capacity. Kennel nights are [start, end) (decision record 0005)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.capacity import find_kennel
from app.enums import SizeClass, Species
from app.models import Facility, Kennel, Owner, Pet, Reservation
from scripts.seed import seed

spec = pytest.mark.spec
MEDIUM, LARGE = SizeClass.MEDIUM, SizeClass.LARGE


@pytest.fixture
async def lodge(session):
    """A facility with medium kennels M1–M3, one large kennel L1, and a medium dog."""
    facility = Facility(name="Test Lodge", timezone="America/Chicago")
    owner = Owner(full_name="Test Owner", email="capacity-owner@example.test")
    session.add_all([facility, owner])
    await session.flush()
    kennels = {
        name: Kennel(facility_id=facility.id, name=name, size_class=size)
        for name, size in [("M1", MEDIUM), ("M2", MEDIUM), ("M3", MEDIUM), ("L1", LARGE)]
    }
    pet = Pet(owner_id=owner.id, name="Biscuit", species=Species.DOG, weight_lb=Decimal(24))
    session.add_all([*kennels.values(), pet])
    await session.flush()

    async def book(kennel_name, start, end):
        session.add(
            Reservation(
                kennel_id=kennels[kennel_name].id, pet_id=pet.id, start_date=start, end_date=end
            )
        )
        await session.flush()

    async def find(size, start, end, facility_id=facility.id):
        kennel = await find_kennel(session, facility_id, size, start, end)
        return kennel.name if kennel else None

    return book, find


MAR = lambda day: date(2027, 3, day)


# --- A kennel is free only if no night overlaps ---------------------------------------


@spec("kennel-capacity", "A kennel is free only if no night overlaps")
async def test_partly_booked_kennels_are_not_free(lodge):
    book, find = lodge
    for name in ("M1", "M2", "M3"):
        await book(name, MAR(6), MAR(9))

    assert await find(MEDIUM, MAR(8), MAR(10)) is None


@spec("kennel-capacity", "A kennel is free only if no night overlaps")
async def test_back_to_back_stay_fits(lodge):
    book, find = lodge
    await book("M1", MAR(6), MAR(9))

    assert await find(MEDIUM, MAR(9), MAR(12)) == "M1"


@spec("kennel-capacity", "A kennel is free only if no night overlaps")
async def test_stay_ending_on_an_existing_check_in_fits(lodge):
    book, find = lodge
    await book("M1", MAR(9), MAR(12))

    assert await find(MEDIUM, MAR(6), MAR(9)) == "M1"


@spec("kennel-capacity", "A kennel is free only if no night overlaps")
async def test_stay_surrounding_an_existing_booking_overlaps(lodge):
    book, find = lodge
    await book("M1", MAR(7), MAR(8))

    assert await find(MEDIUM, MAR(6), MAR(10)) == "M2"


# --- Only the exact size class is searched --------------------------------------------


@spec("kennel-capacity", "Only the exact size class is searched")
async def test_a_free_larger_kennel_is_not_offered(lodge):
    book, find = lodge
    for name in ("M1", "M2", "M3"):
        await book(name, MAR(6), MAR(9))

    assert await find(MEDIUM, MAR(6), MAR(9)) is None
    assert await find(LARGE, MAR(6), MAR(9)) == "L1"


@spec("kennel-capacity", "Only the exact size class is searched")
async def test_other_facilities_are_ignored(lodge, session):
    _, find = lodge
    other = Facility(name="Other Lodge", timezone="America/Denver")
    session.add(other)
    await session.flush()

    assert await find(MEDIUM, MAR(6), MAR(9), facility_id=other.id) is None


# --- The choice among free kennels is deterministic -----------------------------------


@spec("kennel-capacity", "The choice among free kennels is deterministic")
async def test_first_free_kennel_by_name(lodge):
    book, find = lodge
    await book("M1", MAR(6), MAR(9))

    assert await find(MEDIUM, MAR(6), MAR(9)) == "M2"
    assert await find(MEDIUM, MAR(6), MAR(9)) == "M2"


# --- A stay has at least one night ----------------------------------------------------


@spec("kennel-capacity", "A stay has at least one night")
@pytest.mark.parametrize(
    ("start", "end"), [(MAR(6), MAR(6)), (MAR(9), MAR(6))], ids=["zero", "negative"]
)
async def test_stay_without_nights_is_rejected(lodge, start, end):
    _, find = lodge

    with pytest.raises(ValueError, match="night"):
        await find(MEDIUM, start, end)


# --- Search reflects seeded availability ----------------------------------------------


@spec("kennel-capacity", "Search reflects seeded availability")
@pytest.mark.parametrize(
    ("start_in", "end_in", "free"), [(4, 7, False), (8, 10, True)], ids=["full", "free"]
)
async def test_seeded_medium_availability(session, start_in, end_in, free):
    today = date(2027, 3, 1)
    await seed(session, today)
    facility = await session.scalar(select(Facility))

    kennel = await find_kennel(
        session,
        facility.id,
        MEDIUM,
        today + timedelta(days=start_in),
        today + timedelta(days=end_in),
    )

    assert (kennel is not None) == free
