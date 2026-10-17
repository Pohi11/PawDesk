"""Spec: vaccine-compliance, loading rules and records from Postgres (seeded dataset)."""

from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.compliance import Outcome, VaccineStatus, check_pet
from app.enums import Service, Vaccine
from app.models import Facility, Pet
from scripts.seed import seed

spec = pytest.mark.spec
TODAY = date(2027, 3, 1)


@pytest.fixture
async def seeded(session):
    await seed(session, TODAY)
    facility = await session.scalar(select(Facility))
    return session, facility


async def check_seeded(seeded, pet_name, service, start_in, end_in):
    session, facility = seeded
    pet = await session.scalar(select(Pet).where(Pet.name == pet_name))
    start, end = TODAY + timedelta(days=start_in), TODAY + timedelta(days=end_in)
    result = await check_pet(session, pet, facility.id, service, start, end)
    return result, {c.vaccine: c.status for c in result.checks}


@spec("vaccine-compliance", "Rules and records come from the facility and the pet")
async def test_seeded_pet_with_an_expired_vaccine(seeded):
    result, statuses = await check_seeded(seeded, "Pepper", Service.BOARDING, 7, 10)

    assert statuses == {
        Vaccine.RABIES: VaccineStatus.OK,
        Vaccine.DHPP: VaccineStatus.OK,
        Vaccine.BORDETELLA: VaccineStatus.EXPIRED,
    }
    assert result.outcome == Outcome.NOT_COMPLIANT


@spec("vaccine-compliance", "Rules and records come from the facility and the pet")
async def test_seeded_pet_with_unknown_expiry(seeded):
    result, statuses = await check_seeded(seeded, "Olive", Service.BOARDING, 7, 10)

    assert statuses == {
        Vaccine.RABIES: VaccineStatus.OK,
        Vaccine.FVRCP: VaccineStatus.UNKNOWN_EXPIRY,
    }
    assert result.outcome == Outcome.NEEDS_REVIEW


@spec("vaccine-compliance", "Rules and records come from the facility and the pet")
async def test_seeded_pet_whose_rabies_expires_during_its_booked_stay(seeded):
    result, statuses = await check_seeded(seeded, "Moose", Service.BOARDING, 21, 28)

    assert statuses[Vaccine.RABIES] == VaccineStatus.EXPIRES_DURING_STAY
    assert result.outcome == Outcome.NOT_COMPLIANT


@spec("vaccine-compliance", "Rules and records come from the facility and the pet")
async def test_rules_follow_the_service(seeded):
    # Grooming only requires rabies, so Pepper's expired bordetella doesn't matter there.
    result, statuses = await check_seeded(seeded, "Pepper", Service.GROOMING, 7, 7)

    assert statuses == {Vaccine.RABIES: VaccineStatus.OK}
    assert result.outcome == Outcome.COMPLIANT
