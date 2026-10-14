"""Spec: demo-generator, random requests and their certificates against a seeded database."""

from collections import Counter

import pytest
from sqlalchemy import select

from app.certificate_card import render
from app.compliance import Outcome, VaccineEvidence, VaccineStatus, check, load_requirements
from app.demo import DEMO_TODAY
from app.demo_generator import SCENARIOS, generate
from app.enums import Service, Species, Vaccine
from app.models import Facility, Owner, Pet
from scripts.seed import seed

spec = pytest.mark.spec
SEEDS = range(1, 81)
FAILING = {
    "expired": VaccineStatus.EXPIRED,
    "expires_during_stay": VaccineStatus.EXPIRES_DURING_STAY,
    "missing": VaccineStatus.MISSING,
}


@pytest.fixture
async def seeded(session):
    await seed(session, DEMO_TODAY)
    return session


@spec("demo-generator", "Random requests are reproducible")
async def test_same_seed_gives_the_same_request_and_image(seeded):
    first, second = await generate(seeded, 42), await generate(seeded, 42)

    assert first == second
    assert render(first) == render(second)
    assert render(first).startswith(b"\x89PNG\r\n\x1a\n")


@spec("demo-generator", "Random requests are reproducible")
async def test_seeds_vary_the_request(seeded):
    generated = [await generate(seeded, s) for s in SEEDS]

    assert len({g.pet for g in generated}) > 1
    assert len({g.service for g in generated}) > 1
    assert set(Counter(g.scenario for g in generated)) == set(SCENARIOS)
    for g in generated:
        nights = (g.end_date - g.start_date).days
        assert 5 <= (g.start_date - DEMO_TODAY).days <= 40
        assert (2 <= nights <= 6) if g.service == Service.BOARDING else nights == 0
        assert g.pet in g.message


@spec("demo-generator", "The certificate matches its request")
async def test_card_names_the_pet_and_its_owner(seeded):
    for s in SEEDS:
        g = await generate(seeded, s)
        owner = await seeded.scalar(
            select(Owner.full_name).join(Pet, Pet.owner_id == Owner.id).where(Pet.name == g.pet)
        )
        assert g.owner == owner


@spec("demo-generator", "The certificate matches its request")
async def test_scenario_dates_give_the_described_status(seeded):
    facility_id = await seeded.scalar(select(Facility.id))
    for s in SEEDS:
        g = await generate(seeded, s)
        required = await load_requirements(
            seeded, facility_id, Service(g.service), Species(g.species)
        )
        evidence = [
            VaccineEvidence(Vaccine(r.vaccine), r.administered_on, r.expires_on) for r in g.records
        ]

        result = check(required, evidence, g.start_date, g.end_date)

        statuses = [c.status for c in result.checks]
        if g.scenario == "current":
            assert result.outcome == Outcome.COMPLIANT, (s, g.scenario)
        else:
            assert statuses.count(FAILING[g.scenario]) == 1, (s, g.scenario, statuses)
            assert statuses.count(VaccineStatus.OK) == len(statuses) - 1, (s, statuses)
        assert g.scenario_text  # always described in words
