"""Random demo requests with a matching vaccine certificate (spec: demo-generator).

Everything is decided by `random.Random(seed)` and the seeded data (owners, rules), so a seed
always gives the same request and the same card, before and after it is sent. The pet is
invented from the seed and added to its owner only when the request is sent.

A fresh name comes from choosing the seed (`fresh_seed`), not from the generator, which
would otherwise depend on what has been sent (change demo-new-pets, design D2).
"""

import random
import secrets
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance import load_requirements
from app.demo import DEMO_TODAY, NewPet
from app.enums import Service, Species, Vaccine
from app.models import Facility, Owner, Pet, VaccineRule

SCENARIOS = ("current", "expired", "expires_during_stay", "missing")
SCENARIO_WEIGHTS = (40, 20, 20, 20)
SERVICE_WEIGHTS = {Service.BOARDING: 3, Service.DAYCARE: 1, Service.GROOMING: 1}
MAX_SEED = 2**31 - 1
FRESH_DRAWS = 200  # seeds tried for an unused name before the last one is kept
DOG_SHARE = 0.75

# Names for invented pets. None is a seeded pet's name or appears in a sample's message
# (tests/test_demo_generator.py checks both).
NAMES = {
    Species.DOG: [
        "Juno",
        "Pickle",
        "Maple",
        "Ziggy",
        "Clover",
        "Bodhi",
        "Nacho",
        "Hazel",
        "Ollie",
        "Pretzel",
        "Mabel",
        "Rocket",
        "Poppy",
        "Bruno",
        "Daisy",
        "Finn",
        "Ginger",
        "Hank",
        "Ivy",
        "Jasper",
        "Koda",
        "Lulu",
        "Milo",
        "Nala",
        "Oreo",
        "Peanut",
        "Quinn",
        "Rufus",
        "Sadie",
        "Theo",
        "Uma",
        "Violet",
        "Winnie",
        "Yogi",
        "Zeus",
        "Archie",
        "Bella",
        "Cooper",
        "Dexter",
        "Ellie",
        "Fudge",
        "Gus",
        "Harley",
        "Indie",
        "Jack",
        "Kona",
        "Louie",
        "Marley",
        "Nova",
        "Otis",
        "Penny",
        "Remy",
        "Scout",
        "Toby",
        "Ruby",
        "Waylon",
        "Bailey",
        "Chester",
        "Dolly",
        "Ember",
        "Frankie",
        "Goose",
        "Honey",
        "Iggy",
        "Jolene",
        "Kip",
        "Luna",
        "Murphy",
        "Nugget",
        "Ozzy",
        "Pippin",
        "Rosco",
        "Sprout",
        "Tucker",
        "Ripley",
        "Benji",
        "Cosmo",
        "Duke",
        "Echo",
        "Fitz",
        "Gizmo",
        "Hobbes",
        "Izzy",
        "Jet",
        "Kai",
        "Leo",
        "Ned",
        "Opal",
        "Pax",
        "Rory",
        "Sage",
        "Tank",
        "Vinny",
        "Wally",
        "Xena",
        "Yuki",
        "Bear",
        "Barnaby",
        "Captain",
        "Dash",
        "Elvis",
        "Flash",
        "Gatsby",
        "Huckleberry",
        "Jiffy",
        "Kobe",
        "Lucky",
        "Nemo",
        "Noble",
        "Oakley",
        "Pumba",
        "Rascal",
        "Sherlock",
        "Tater",
        "Willis",
        "Banjo",
        "Chewie",
        "Domino",
        "Frodo",
        "Gunner",
    ],
    Species.CAT: [
        "Miso",
        "Cleo",
        "Pumpkin",
        "Smokey",
        "Whiskers",
        "Salem",
        "Mittens",
        "Noodle",
        "Pixel",
        "Sushi",
        "Biscotti",
        "Marmalade",
        "Felix",
        "Simba",
        "Tigger",
        "Shadow",
        "Jinx",
        "Willow",
        "Basil",
        "Chai",
        "Dumpling",
        "Figaro",
        "Gnocchi",
        "Hamlet",
        "Inky",
        "Kiki",
        "Lychee",
        "Mango",
        "Nutmeg",
        "Onyx",
        "Paprika",
        "Quill",
        "Raisin",
        "Saffron",
        "Truffle",
        "Udon",
        "Velvet",
        "Wasabi",
        "Yoshi",
        "Zuzu",
        "Ash",
        "Bean",
        "Cinder",
        "Dot",
        "Fig",
        "Gigi",
        "Jellybean",
        "Kit",
        "Lola",
        "Moxie",
        "Nori",
        "Pistachio",
        "Ramen",
        "Sesame",
        "Tinsel",
        "Vesper",
        "Wren",
        "Yarrow",
        "Zinnia",
        "Clementine",
    ],
}
# (breed, lightest, heaviest) in pounds. Breeds in the dashboard's photo set come first.
BREEDS = {
    Species.DOG: [
        ("Beagle", 20, 30),
        ("Border Collie", 30, 45),
        ("Labrador Retriever", 55, 80),
        ("Bernese Mountain Dog", 80, 110),
        ("Chihuahua", 4, 6),
        ("Pembroke Welsh Corgi", 24, 30),
        ("Golden Retriever", 55, 75),
        ("Dachshund", 16, 32),
        ("Boxer", 50, 70),
        ("Shih Tzu", 9, 16),
        ("Standard Poodle", 40, 70),
        ("Australian Shepherd", 40, 65),
        ("Great Dane", 110, 160),
        ("Mixed Breed", 15, 70),
    ],
    Species.CAT: [
        ("Domestic Shorthair", 8, 14),
        ("Ragdoll", 10, 20),
        ("Maine Coon", 10, 25),
        ("Siamese", 6, 12),
        ("Domestic Longhair", 8, 15),
    ],
}

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
    breed: str
    weight_lb: float
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

    def new_pet(self) -> NewPet:
        """The pet to add to its owner when the request is sent."""
        return NewPet(self.pet, Species(self.species), self.breed, self.weight_lb)


def spoken(day: date) -> str:
    """How a pet parent writes a date: "March 12"."""
    return f"{day.strftime('%B')} {day.day}"


def printed(day: date) -> str:
    """How a clinic prints a date: "Mar 12, 2027"."""
    return f"{day.strftime('%b')} {day.day}, {day.year}"


def invent_pet(rng: random.Random) -> NewPet:
    """The pet, from the first draws of the seed's random sequence."""
    species = Species.DOG if rng.random() < DOG_SHARE else Species.CAT
    name = rng.choice(NAMES[species])
    breed, lightest, heaviest = rng.choice(BREEDS[species])
    return NewPet(name, species, breed, round(rng.uniform(lightest, heaviest), 1))


def pet_name(seed: int) -> str:
    """The name `generate` gives seed's pet, without touching the database."""
    return invent_pet(random.Random(seed)).name


async def fresh_seed(
    session: AsyncSession,
    avoid: Iterable[str] = (),
    draw: Callable[[], int] = lambda: secrets.randbelow(MAX_SEED + 1),
) -> int:
    """A random seed whose pet name is on no pet on file and none of `avoid`, ignoring case.
    After FRESH_DRAWS tries the last draw is kept, so a used-up pool still gives a request."""
    taken = {name.strip().casefold() for name in await session.scalars(select(Pet.name))}
    taken |= {name.strip().casefold() for name in avoid}
    seed = draw()
    for _ in range(FRESH_DRAWS - 1):
        if pet_name(seed).casefold() not in taken:
            break
        seed = draw()
    return seed


async def generate(session: AsyncSession, seed: int) -> GeneratedRequest:
    rng = random.Random(seed)
    pet = invent_pet(rng)
    owners = list(await session.scalars(select(Owner).order_by(Owner.email)))
    facility_id = await session.scalar(select(Facility.id).order_by(Facility.id).limit(1))
    if not owners or facility_id is None:
        raise LookupError("demo data is missing: run the seed script first")
    owner = rng.choice(owners)

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
    scenario = rng.choices(SCENARIOS, weights=SCENARIO_WEIGHTS)[0]
    if scenario == "expires_during_stay" and nights < 2:
        scenario = "expired"  # a one-day visit has no day before checkout
    required = sorted(await load_requirements(session, facility_id, service, pet.species))
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
        breed=pet.breed,
        weight_lb=pet.weight_lb,
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
    """The card's records and the scenario in words. The pet is new, with no records on file,
    so the card alone decides each vaccine's status."""

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
        target = rng.choice(required)
        label = VACCINE_LABEL[target]
        if scenario == "missing":
            del records[target]
            text = f"{label} is not on the card."
        else:
            if scenario == "expired":
                expires = start - timedelta(days=rng.randint(5, 60))
                text = f"{label} expired on {printed(expires)}, before the stay."
            else:
                expires = start + timedelta(days=rng.randint(0, (end - start).days - 1))
                text = f"{label} expires on {printed(expires)}, during the stay."
            records[target] = CardRecord(str(target), label, expires - timedelta(days=365), expires)
    ordered = sorted(records.values(), key=lambda r: list(VACCINE_LABEL).index(Vaccine(r.vaccine)))
    return ordered, text
