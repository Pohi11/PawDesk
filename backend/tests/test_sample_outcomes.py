"""Spec: observability-api, each sample's promise follows from fixed data (change
records-year-fidelity, design D6). No model: the seeded records on file plus the records
each card was drawn from, checked as the orchestrator checks them, on the hosted dataset."""

import pytest
from sqlalchemy import select

from app.capacity import find_kennel, find_pet_stay
from app.compliance import (
    Outcome,
    VaccineEvidence,
    VaccineStatus,
    check,
    load_evidence,
    load_requirements,
)
from app.demo import DEMO_TODAY, SAMPLES
from app.enums import Vaccine
from app.models import Facility, Pet
from scripts.draw_sample_cards import CARDS
from scripts.seed import seed

spec = pytest.mark.spec
REQ = "Samples end as promised from seeded and printed records"


def printed(sample_id):
    _, drawn = CARDS[sample_id]
    return [
        VaccineEvidence(Vaccine(r.vaccine), r.administered_on, r.expires_on)
        for r in drawn().records
    ]


@pytest.fixture
async def hosted(session):
    await seed(session, DEMO_TODAY, requests=False)  # as the hosted demo starts
    return session


async def outcome(session, sample_id, *, card=True):
    sample = SAMPLES[sample_id]
    facility = await session.scalar(select(Facility))
    pet = await session.scalar(select(Pet).where(Pet.name == sample.pet))
    required = await load_requirements(session, facility.id, sample.service, pet.species)
    records = await load_evidence(session, pet.id) + (printed(sample_id) if card else [])
    result = check(required, records, sample.start_date, sample.end_date)
    booked = await find_pet_stay(session, pet.id, sample.start_date, sample.end_date)
    kennel = await find_kennel(
        session, facility.id, pet.size_class, sample.start_date, sample.end_date
    )
    return result, booked, kennel


@spec("observability-api", REQ)
async def test_clean_sample_passes_on_its_records(hosted):
    result, booked, kennel = await outcome(hosted, "clean")
    assert result.outcome == Outcome.COMPLIANT
    assert booked is None and kennel is not None and kennel.size_class == "medium"


@spec("observability-api", REQ)
async def test_injection_sample_passes_on_its_records(hosted):
    result, booked, kennel = await outcome(hosted, "injection")
    assert result.outcome == Outcome.COMPLIANT
    assert booked is None and kennel is not None


@spec("observability-api", REQ)
async def test_expired_vaccine_sample_fails_only_on_bordetella(hosted):
    result, booked, kennel = await outcome(hosted, "expired-vaccine")
    assert {c.vaccine: c.status for c in result.checks if c.status != VaccineStatus.OK} == {
        Vaccine.BORDETELLA: VaccineStatus.EXPIRED
    }
    assert booked is None and kennel is not None and kennel.size_class == "large"


@spec("observability-api", REQ)
async def test_clean_sample_does_not_hang_on_the_card_read(hosted):
    result, _, _ = await outcome(hosted, "clean", card=False)
    assert result.outcome == Outcome.COMPLIANT
