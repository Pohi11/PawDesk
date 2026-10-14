"""Random demo requests with a matching vaccine certificate (spec: demo-generator).

Everything is decided by `random.Random(seed)` and the seeded database, so a seed always
gives the same request and the same card. Nothing is stored until the request is sent.
"""

import random
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance import load_requirements
from app.demo import DEMO_TODAY
from app.enums import Service, Species, Vaccine
from app.models import Facility, Owner, Pet, VaccineRule

SCENARIOS = ("current", "expired", "expires_during_stay", "missing")
SCENARIO_WEIGHTS = (40, 20, 20, 20)
SERVICE_WEIGHTS = {Service.BOARDING: 3, Service.DAYCARE: 1, Service.GROOMING: 1}

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
    pet, owner = rng.choice(rows)
    facility_id = await session.scalar(select(Facility.id).order_by(Facility.id).limit(1))

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

    required = sorted(await load_requirements(session, facility_id, service, pet.species))
    scenario = rng.choices(SCENARIOS, weights=SCENARIO_WEIGHTS)[0]
    if scenario == "expires_during_stay" and nights < 2:
        scenario = "expired"
    records, scenario_text = _records(rng, pet.species, required, start, end, scenario)

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
    start: date,
    end: date,
    scenario: str,
) -> tuple[list[CardRecord], str]:
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

    target = rng.choice(required)
    label = VACCINE_LABEL[target]
    if scenario == "expired":
        expires = start - timedelta(days=rng.randint(5, 60))
        records[target] = CardRecord(str(target), label, expires - timedelta(days=365), expires)
        text = f"{label} expired on {printed(expires)}, before the stay."
    elif scenario == "expires_during_stay":
        expires = start + timedelta(days=rng.randint(0, (end - start).days - 1))
        records[target] = CardRecord(str(target), label, expires - timedelta(days=365), expires)
        text = f"{label} expires on {printed(expires)}, during the stay."
    elif scenario == "missing":
        del records[target]
        text = f"{label} is not on the card."
    else:
        text = "Every vaccine on the card is current for the whole stay."
    ordered = sorted(records.values(), key=lambda r: list(VACCINE_LABEL).index(Vaccine(r.vaccine)))
    return ordered, text
