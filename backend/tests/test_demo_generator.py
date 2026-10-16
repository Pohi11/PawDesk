"""Spec: demo-generator, random requests and their certificates against a seeded database."""

import io
import itertools
import re
from collections import Counter
from decimal import Decimal

import pytest
from PIL import Image
from sqlalchemy import select

from app.certificate_card import HEIGHT, PAPER, WIDTH, render
from app.compliance import (
    Outcome,
    VaccineEvidence,
    VaccineStatus,
    check,
    load_evidence,
    load_requirements,
)
from app.demo import DEMO_TODAY, SAMPLE_CARDS, SAMPLES
from app.demo_generator import (
    BREEDS,
    FRESH_DRAWS,
    NAMES,
    SCENARIOS,
    VACCINE_LABEL,
    fresh_seed,
    generate,
    pet_name,
    printed,
)
from app.enums import Service, Species, Vaccine
from app.models import Facility, Owner, Pet
from scripts.seed import PETS, seed

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


async def add_pet(session, name: str) -> None:
    owner_id = await session.scalar(select(Owner.id).limit(1))
    session.add(
        Pet(owner_id=owner_id, name=name, species=Species.DOG, breed=None, weight_lb=Decimal(20))
    )
    await session.flush()


def seed_named(name: str) -> int:
    return next(s for s in itertools.count() if pet_name(s) == name)


def seeds_with_different_names() -> tuple[int, int]:
    first = 0
    second = next(s for s in itertools.count(1) if pet_name(s) != pet_name(first))
    return first, second


@spec("demo-generator", "Random requests are reproducible")
async def test_same_seed_gives_the_same_request_and_image(seeded):
    before = await generate(seeded, 42)
    await add_pet(seeded, before.pet)  # as if seed 42 had been sent

    after = await generate(seeded, 42)

    assert before == after
    assert render(before) == render(after)
    assert render(before).startswith(b"\x89PNG\r\n\x1a\n")


@spec("demo-generator", "Random requests are reproducible")
async def test_seeds_vary_the_request(seeded):
    generated = [await generate(seeded, s) for s in SEEDS]

    assert len({g.pet for g in generated}) > 40
    assert {g.species for g in generated} == {"dog", "cat"}
    assert len({g.service for g in generated}) > 1
    assert set(Counter(g.scenario for g in generated)) == set(SCENARIOS)
    for g in generated:
        nights = (g.end_date - g.start_date).days
        assert 5 <= (g.start_date - DEMO_TODAY).days <= 40
        assert (2 <= nights <= 6) if g.service == Service.BOARDING else nights == 0
        assert g.pet in g.message


@spec("demo-generator", "Generated pets are new")
def test_the_pool_stays_clear_of_other_names():
    dogs, cats = NAMES[Species.DOG], NAMES[Species.CAT]
    pool = [name.casefold() for name in dogs + cats]
    seeded_names = {name.casefold() for _, name, *_ in PETS}
    sample_words = {
        word.casefold()
        for sample in SAMPLES.values()
        for word in re.findall(r"\w+", sample.message)
    }

    assert len(dogs) >= 100 and len(cats) >= 50
    assert len(pool) == len(set(pool))
    assert not set(pool) & seeded_names
    assert not set(pool) & sample_words


@spec("demo-generator", "Generated pets are new")
async def test_the_pet_is_new_with_a_fitting_breed_and_weight(seeded):
    on_file = {name for name in await seeded.scalars(select(Pet.name))}
    for s in SEEDS:
        g = await generate(seeded, s)
        ranges = {breed: (low, high) for breed, low, high in BREEDS[Species(g.species)]}
        low, high = ranges[g.breed]
        assert g.pet in NAMES[Species(g.species)] and g.pet not in on_file
        assert low <= g.weight_lb <= high


@spec("demo-generator", "The certificate matches its request")
async def test_card_names_a_seeded_owner(seeded):
    owners = {name for name in await seeded.scalars(select(Owner.full_name))}
    for s in SEEDS:
        g = await generate(seeded, s)
        assert g.owner in owners
        assert g.owner_email.endswith("@example.test")


@spec("demo-generator", "The certificate matches its request")
async def test_card_dates_match_the_scenario_text(seeded):
    for s in SEEDS:
        g = await generate(seeded, s)
        labels = [r.label for r in g.records]
        if g.scenario == "current":
            assert all(
                r.administered_on <= g.start_date <= g.end_date <= r.expires_on for r in g.records
            ), s
            continue
        if g.scenario == "missing":
            missing = g.scenario_text.removesuffix(" is not on the card.")
            assert missing in VACCINE_LABEL.values() and missing not in labels, s
            continue
        (record,) = [r for r in g.records if g.scenario_text.startswith(r.label + " ")]
        assert printed(record.expires_on) in g.scenario_text, s
        if g.scenario == "expired":
            assert record.expires_on < g.start_date, s
        else:
            assert g.start_date <= record.expires_on < g.end_date, s


@spec("demo-generator", "Scenarios hold with the records on file")
async def test_scenario_holds_with_the_records_on_file(seeded):
    """The desk checks the card together with the records on file, so the test does too."""
    facility_id = await seeded.scalar(select(Facility.id))
    for s in SEEDS:
        g = await generate(seeded, s)
        required = await load_requirements(
            seeded, facility_id, Service(g.service), Species(g.species)
        )
        pet_id = await seeded.scalar(select(Pet.id).where(Pet.name == g.pet))
        on_file = await load_evidence(seeded, pet_id) if pet_id else []
        evidence = on_file + [
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


@spec("demo-generator", "New names avoid names in use")
async def test_a_name_on_file_is_skipped(seeded):
    juno, other = seed_named("Juno"), seeds_with_different_names()[1]
    if pet_name(other) == "Juno":
        other = seeds_with_different_names()[0]
    await add_pet(seeded, "juno")  # case is ignored
    draws = iter([juno, other])

    chosen = await fresh_seed(seeded, draw=lambda: next(draws))

    assert chosen == other
    assert pet_name(chosen) != "Juno"


@spec("demo-generator", "New names avoid names in use")
async def test_recent_names_are_skipped(seeded):
    first, second = seeds_with_different_names()
    draws = iter([first, second])

    chosen = await fresh_seed(
        seeded, avoid=[f" {pet_name(first).upper()} "], draw=lambda: next(draws)
    )

    assert chosen == second


@spec("demo-generator", "New names avoid names in use")
async def test_a_used_up_pool_still_gives_a_seed(seeded):
    calls = []

    def draw() -> int:
        calls.append(7)
        return 7

    chosen = await fresh_seed(seeded, avoid=[pet_name(7)], draw=draw)

    assert chosen == 7
    assert len(calls) == FRESH_DRAWS


# --- Demo cards are marked synthetic in metadata ----------------------------------------


@spec("demo-generator", "Demo cards are marked synthetic in metadata")
async def test_nothing_below_the_signature(seeded):
    card = Image.open(io.BytesIO(render(await generate(seeded, 42)))).convert("RGB")
    below_label = card.crop((0, HEIGHT - 44, WIDTH, HEIGHT))  # the label ends ~50 px up

    assert below_label.getcolors() == [(WIDTH * 44, PAPER)]


@spec("demo-generator", "Demo cards are marked synthetic in metadata")
@pytest.mark.parametrize("card", ["generated", *sorted(SAMPLE_CARDS.glob("*.png"))], ids=str)
async def test_cards_are_marked_in_metadata(seeded, card):
    data = render(await generate(seeded, 42)) if card == "generated" else card.read_bytes()

    comment = Image.open(io.BytesIO(data)).text["Comment"]

    assert comment.startswith("Synthetic PawDesk demo certificate.")
