"""Random demo requests with a matching vaccine certificate (spec: demo-generator).

Everything is decided by `random.Random(seed)` and the seeded database, so a seed always
gives the same request and the same card. Nothing is stored until the request is sent.

The desk checks a card together with the pet's records on file, so a scenario is only used
where the real compliance check, given both, agrees with it (design D3).
"""

import random
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance import (
    VaccineEvidence,
    VaccineStatus,
    load_evidence,
    load_requirements,
    vaccine_status,
)
from app.demo import DEMO_TODAY
from app.enums import Service, Species, Vaccine
from app.models import Facility, Owner, Pet, VaccineRule

SCENARIOS = ("current", "expired", "expires_during_stay", "missing")
SCENARIO_WEIGHTS = (40, 20, 20, 20)
SERVICE_WEIGHTS = {Service.BOARDING: 3, Service.DAYCARE: 1, Service.GROOMING: 1}
EXPECTED = {
    "expired": VaccineStatus.EXPIRED,
    "expires_during_stay": VaccineStatus.EXPIRES_DURING_STAY,
    "missing": VaccineStatus.MISSING,
}
ATTEMPTS = 30  # draws of pet, service, and stay before a failing scenario gives way

VACCINE_LABEL = {
    Vaccine.RABIES: "Rabies",
    Vaccine.DHPP: "DHPP",
    Vaccine.BORDETELLA: "Bordetella",
    Vaccine.CANINE_INFLUENZA: "Canine Influenza",
    Vaccine.LEPTOSPIROSIS: "Leptospirosis",
    Vaccine.FVRCP: "FVRCP",
    Vaccine.FELV: "FeLV",
}
OPTIONAL = {
    Species.DOG: [Vaccine.LEPTOSPIROSIS, Vaccine.CANINE_INFLUENZA],
    Species.CAT: [Vaccine.FELV],
}

CLINICS = [
    ("Willow Creek Animal Hospital", "Dr. Nora Delacroix"),
    ("Juniper Hill Veterinary Clinic", "Dr. Sam Okonkwo"),
    ("Bramblewood Pet Care", "Dr. Lena Marsh"),
    ("Cedar Lane Veterinary Group", "Dr. Theo Vance"),
]

MESSAGES = {
    Service.BOARDING: [
        "Hi! Could {pet} board with you from {start} to {end}?",
        "Hello, I'd like to book boarding for {pet}, {start} through {end}.",
        "Do you have room for {pet} from {start} to {end}? We'll be out of town.",
    ],
    Service.DAYCARE: [
        "Can {pet} come for daycare on {start}?",
        "Hi, is there a daycare spot for {pet} on {start}?",
    ],
    Service.GROOMING: [
        "{pet} needs a groom on {start}, please.",
        "Could I book a grooming appointment for {pet} on {start}?",
    ],
}
NOTES = [
    "",
    " Their vaccine card is attached.",
    " They eat twice a day.",
    " They get a little nervous at drop-off.",
    " Updated shot record attached.",
]


@dataclass(frozen=True)
class CardRecord:
    vaccine: str
    label: str
    administered_on: date
    expires_on: date


@dataclass(frozen=True)
class GeneratedRequest:
    seed: int
    owner_email: str
    owner: str
    pet: str
    species: str
    service: str
    start_date: date
    end_date: date
    message: str
    scenario: str
    scenario_text: str
    clinic: str
    vet: str
    records: list[CardRecord] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        data = asdict(self)
        for key in ("start_date", "end_date"):
            data[key] = data[key].isoformat()
        data["records"] = [
            r
            | {
                "administered_on": r["administered_on"].isoformat(),
                "expires_on": r["expires_on"].isoformat(),
            }
            for r in data["records"]
        ]
        data.pop("owner_email")
        return data


def spoken(day: date) -> str:
    """How a pet parent writes a date: "March 12"."""
    return f"{day.strftime('%B')} {day.day}"


def printed(day: date) -> str:
    """How a clinic prints a date: "Mar 12, 2027"."""
    return f"{day.strftime('%b')} {day.day}, {day.year}"


async def generate(session: AsyncSession, seed: int) -> GeneratedRequest:
    rng = random.Random(seed)
    rows = (
        await session.execute(
            select(Pet, Owner).join(Owner, Owner.id == Pet.owner_id).order_by(Pet.name, Pet.id)
        )
    ).all()
    if not rows:
        raise LookupError("demo data is missing: run the seed script first")
    facility_id = await session.scalar(select(Facility.id).order_by(Facility.id).limit(1))
    scenario = rng.choices(SCENARIOS, weights=SCENARIO_WEIGHTS)[0]

    for attempt in range(ATTEMPTS + 1):
        if attempt == ATTEMPTS:
            scenario = "current"  # holds for any pet: the card covers every vaccine
        pet, owner = rng.choice(rows)
        offered = sorted(
            set(
                await session.scalars(
                    select(VaccineRule.service).where(VaccineRule.species == pet.species)
                )
            )
        )
        service = rng.choices(offered, weights=[SERVICE_WEIGHTS[s] for s in offered])[0]
        start = DEMO_TODAY + timedelta(days=rng.randint(5, 40))
        nights = rng.randint(2, 6) if service == Service.BOARDING else 0
        end = start + timedelta(days=nights)
        if scenario == "expires_during_stay" and nights < 2:
            continue
        required = sorted(await load_requirements(session, facility_id, service, pet.species))
        on_file = await load_evidence(session, pet.id)
        drawn = _records(rng, pet.species, required, on_file, start, end, scenario)
        if drawn is not None:
            break
    records, scenario_text = drawn

    template = rng.choice(MESSAGES[service])
    message = template.format(pet=pet.name, start=spoken(start), end=spoken(end)) + rng.choice(
        NOTES
    )
    clinic, vet = rng.choice(CLINICS)
    return GeneratedRequest(
        seed=seed,
        owner_email=owner.email,
        owner=owner.full_name,
        pet=pet.name,
        species=str(pet.species),
        service=str(service),
        start_date=start,
        end_date=end,
        message=message,
        scenario=scenario,
        scenario_text=scenario_text,
        clinic=clinic,
        vet=vet,
        records=records,
    )


def _records(
    rng: random.Random,
    species: Species,
    required: list[Vaccine],
    on_file: list[VaccineEvidence],
    start: date,
    end: date,
    scenario: str,
) -> tuple[list[CardRecord], str] | None:
    """The card's records and the scenario in words, or None when no required vaccine can
    show the scenario because the records on file already decide it."""

    def current(vaccine: Vaccine) -> CardRecord:
        given = start - timedelta(days=rng.randint(60, 330))
        years = 3 if vaccine == Vaccine.RABIES and rng.random() < 0.5 else 1
        expires = (
            given.replace(year=given.year + years)
            if not (given.month == 2 and given.day == 29)
            else given + timedelta(days=365 * years)
        )
        expires = max(expires, end + timedelta(days=30))  # always well past checkout
        return CardRecord(str(vaccine), VACCINE_LABEL[vaccine], given, expires)

    records = {v: current(v) for v in required}
    extras = [v for v in OPTIONAL.get(species, []) if v not in records]
    if extras and rng.random() < 0.5:
        extra = rng.choice(extras)
        records[extra] = current(extra)

    if scenario == "current":
        text = "Every vaccine on the card is current for the whole stay."
    else:
        expires = None
        if scenario == "expired":
            expires = start - timedelta(days=rng.randint(5, 60))
        elif scenario == "expires_during_stay":
            expires = start + timedelta(days=rng.randint(0, (end - start).days - 1))

        def shows_scenario(vaccine: Vaccine) -> bool:
            evidence = [r for r in on_file if r.vaccine == vaccine]
            if expires is not None:
                evidence.append(VaccineEvidence(vaccine, expires - timedelta(days=365), expires))
            return vaccine_status(evidence, start, end) == EXPECTED[scenario]

        candidates = [v for v in required if shows_scenario(v)]
        if not candidates:
            return None
        target = rng.choice(candidates)
        label = VACCINE_LABEL[target]
        if expires is None:
            del records[target]
            text = f"{label} is not on the card or on file."
        else:
            records[target] = CardRecord(str(target), label, expires - timedelta(days=365), expires)
            when = "before the stay" if scenario == "expired" else "during the stay"
            verb = "expired" if scenario == "expired" else "expires"
            text = f"{label} {verb} on {printed(expires)}, {when}."
    ordered = sorted(records.values(), key=lambda r: list(VACCINE_LABEL).index(Vaccine(r.vaccine)))
    return ordered, text
