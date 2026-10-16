"""Load the synthetic development dataset (spec: seed-data, design D14).

Run from backend/:  uv run python -m scripts.seed [--no-requests]

Deletes every row in the domain tables, then loads a fixed, fictional dataset in one
transaction. Dates are relative to today, so "expires during an upcoming stay" stays true
whenever the seed is run. Refuses anything but a local database, or the one remote host
named in PAWDESK_SEED_ALLOWED_HOST (the hosted demo resets itself on start).
--no-requests leaves out the example booking requests (the hosted demo starts with none).
"""

import asyncio
import os
import sys
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import make_engine, make_sessionmaker
from app.enums import ApprovalAction, Service, SizeClass, Species, Vaccine
from app.lifecycle import Actor, State
from app.models import (
    Approval,
    Base,
    BookingRequest,
    Facility,
    Kennel,
    Owner,
    Pet,
    Reservation,
    VaccineRecord,
    VaccineRule,
)
from app.transitions import transition

LOCAL_HOSTS = {"localhost", "127.0.0.1", "postgres"}


class SeedRefused(Exception):
    """The target database is not a local development or test database."""


def ensure_local(database_url: str, allowed_host: str | None = None) -> None:
    """Refuse every host but a local one or exactly `allowed_host`.

    Naming the host, rather than a yes/no switch, means a mistyped DATABASE_URL is still
    refused (change public-demo-hosting, design D4).
    """
    host = make_url(database_url).host
    if host not in LOCAL_HOSTS and not (allowed_host and host == allowed_host):
        raise SeedRefused(f"refusing to seed non-local database host {host!r}")


async def reset(session: AsyncSession) -> None:
    # One TRUNCATE for every table: faster than DELETE, and CASCADE handles foreign keys.
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    await session.execute(text(f"TRUNCATE {tables} CASCADE"))


RULES = {
    (Service.BOARDING, Species.DOG): [Vaccine.RABIES, Vaccine.DHPP, Vaccine.BORDETELLA],
    (Service.BOARDING, Species.CAT): [Vaccine.RABIES, Vaccine.FVRCP],
    (Service.DAYCARE, Species.DOG): [
        Vaccine.RABIES,
        Vaccine.DHPP,
        Vaccine.BORDETELLA,
        Vaccine.CANINE_INFLUENZA,
    ],
    (Service.DAYCARE, Species.CAT): [Vaccine.RABIES, Vaccine.FVRCP],
    (Service.GROOMING, Species.DOG): [Vaccine.RABIES],
    (Service.GROOMING, Species.CAT): [Vaccine.RABIES],
}

KENNELS = {
    SizeClass.SMALL: ["S1", "S2", "S3"],
    SizeClass.MEDIUM: ["M1", "M2", "M3"],
    SizeClass.LARGE: ["L1", "L2"],
    SizeClass.XLARGE: ["X1"],
    SizeClass.CAT: ["C1", "C2"],
}

OWNERS = [
    ("Avery Lindqvist", "avery.lindqvist@example.test", "555-0101"),
    ("Mateo Okafor", "mateo.okafor@example.test", "555-0102"),
    ("Priya Venkataraman", "priya.v@example.test", "555-0103"),
    ("Jonah Whitfield", "jonah.whitfield@example.test", "555-0104"),
    ("Sunny Calloway", "sunny.calloway@example.test", "555-0105"),
]

# (owner index, name, species, breed, weight in lb)
PETS = [
    (0, "Biscuit", Species.DOG, "Beagle", "24"),
    (0, "Olive", Species.CAT, "Domestic Shorthair", "11"),
    (1, "Juniper", Species.DOG, "Bernese Mountain Dog", "98"),
    (2, "Pepper", Species.DOG, "Chihuahua", "6"),
    (3, "Moose", Species.DOG, "Labrador Retriever", "72"),
    (3, "Waffles", Species.DOG, "Border Collie", "38"),
    (4, "Rosie", Species.DOG, "Pembroke Welsh Corgi", "28"),
    (4, "Tofu", Species.CAT, "Ragdoll", "14"),
]


async def load(session: AsyncSession, today: date, requests: bool = True) -> None:
    def days(n: int) -> date:
        return today + timedelta(days=n)

    facility = Facility(name="Maple Hollow Pet Lodge", timezone="America/Chicago")
    session.add(facility)
    await session.flush()

    session.add_all(
        VaccineRule(facility_id=facility.id, service=service, species=species, vaccine=vaccine)
        for (service, species), vaccines in RULES.items()
        for vaccine in vaccines
    )
    kennels = {
        name: Kennel(facility_id=facility.id, name=name, size_class=size)
        for size, names in KENNELS.items()
        for name in names
    }
    owners = [
        Owner(full_name=n, email=e, phone=p, emergency_contact_name="Lee Park")
        for n, e, p in OWNERS
    ]
    session.add_all([*kennels.values(), *owners])
    await session.flush()

    pets = {
        name: Pet(
            owner_id=owners[owner].id,
            name=name,
            species=species,
            breed=breed,
            weight_lb=Decimal(weight),
        )
        for owner, name, species, breed, weight in PETS
    }
    session.add_all(pets.values())
    await session.flush()

    def records(pet: str, *entries: tuple[Vaccine, int, int | None]) -> list[VaccineRecord]:
        return [
            VaccineRecord(
                pet_id=pets[pet].id,
                vaccine=vaccine,
                administered_on=days(given),
                expires_on=None if expires is None else days(expires),
            )
            for vaccine, given, expires in entries
        ]

    year = 365
    session.add_all(
        [
            # Fully current.
            *records(
                "Biscuit",
                (Vaccine.RABIES, -200, 3 * year - 200),
                (Vaccine.DHPP, -100, year),
                (Vaccine.BORDETELLA, -60, 120),
            ),
            *records("Juniper", *[(v, -30, year) for v in RULES[Service.DAYCARE, Species.DOG]]),
            *records("Rosie", *[(v, -90, 200) for v in RULES[Service.BOARDING, Species.DOG]]),
            *records("Waffles", *[(v, -20, year) for v in RULES[Service.BOARDING, Species.DOG]]),
            *records("Tofu", (Vaccine.RABIES, -40, year), (Vaccine.FVRCP, -40, year)),
            # Edge case: Bordetella already expired.
            *records(
                "Pepper",
                (Vaccine.RABIES, -300, year),
                (Vaccine.DHPP, -300, 60),
                (Vaccine.BORDETELLA, -200, -20),
            ),
            # Edge case: rabies expires partway through Moose's upcoming stay (days +7..+14).
            *records(
                "Moose",
                (Vaccine.RABIES, -3 * year + 10, 10),
                (Vaccine.DHPP, -50, year),
                (Vaccine.BORDETELLA, -50, 130),
            ),
            # Edge case: certificate shows no expiry date for FVRCP.
            *records("Olive", (Vaccine.RABIES, -100, year), (Vaccine.FVRCP, -100, None)),
        ]
    )

    session.add_all(
        [
            Reservation(
                kennel_id=kennels["L1"].id, pet_id=pets["Moose"].id,
                start_date=days(7), end_date=days(14),
            ),
            # Every medium kennel is taken for days +4..+7, so a medium dog asking for those
            # nights has to be offered alternatives (exercised from Phase 7 on).
            Reservation(
                kennel_id=kennels["M1"].id, pet_id=pets["Rosie"].id,
                start_date=days(4), end_date=days(7),
            ),
            Reservation(
                kennel_id=kennels["M2"].id, pet_id=pets["Biscuit"].id,
                start_date=days(4), end_date=days(7),
            ),
            Reservation(
                kennel_id=kennels["M3"].id, pet_id=pets["Waffles"].id,
                start_date=days(4), end_date=days(7),
            ),
            Reservation(
                kennel_id=kennels["M1"].id, pet_id=pets["Biscuit"].id,
                start_date=days(30), end_date=days(33),
            ),
            Reservation(
                kennel_id=kennels["C1"].id, pet_id=pets["Tofu"].id,
                start_date=days(2), end_date=days(5),
            ),
        ]
    )  # fmt: skip
    await session.flush()
    if not requests:
        return

    def request(owner: int, pet: str | None, message: str) -> BookingRequest:
        return BookingRequest(
            facility_id=facility.id,
            owner_id=owners[owner].id,
            pet_id=pets[pet].id if pet else None,
            raw_message=message,
        )

    new = request(1, None, "Hi! Can Juniper board with you for 4 nights starting next Friday?")
    flagged = request(2, "Pepper", "Pepper needs daycare Tuesday and Thursday next week please")
    done = request(4, "Tofu", "Booking Tofu for boarding in two days, three nights. Thanks!")
    broken = request(3, "Moose", "can moose come stay?? photo of his shots attached")
    reviewed = request(0, "Biscuit", "Could Biscuit get a bath and nail trim this Saturday?")
    session.add_all([new, flagged, done, broken, reviewed])
    await session.flush()

    # Advance through the transition service so the log matches each request's state.
    system = Actor.SYSTEM
    for target in (State.EXTRACTING, State.CHECKING, State.RESOLVING, State.DRAFTING):
        await transition(session, flagged, target, system)
    await transition(session, flagged, State.NEEDS_REVIEW, system, reason="bordetella expired")

    for target in (State.EXTRACTING, State.CHECKING, State.DRAFTING, State.READY):
        await transition(session, done, target, system)
    await transition(session, done, State.APPROVED, system, reason="all checks clear")
    await transition(session, done, State.SENT, system)

    await transition(session, broken, State.EXTRACTING, system)
    await transition(session, broken, State.FAILED, system, error="model request timed out")

    for target in (State.EXTRACTING, State.CHECKING, State.DRAFTING):
        await transition(session, reviewed, target, system)
    await transition(session, reviewed, State.NEEDS_REVIEW, system, reason="low confidence")
    session.add(
        Approval(
            booking_request_id=reviewed.id,
            action=ApprovalAction.APPROVE,
            staff_name="Dana Reyes",
        )
    )
    await transition(session, reviewed, State.APPROVED, Actor.STAFF)


async def seed(session: AsyncSession, today: date, requests: bool = True) -> None:
    await reset(session)
    await load(session, today, requests)


async def table_counts(session: AsyncSession) -> dict[str, int]:
    return {
        t.name: await session.scalar(select(func.count()).select_from(t))
        for t in Base.metadata.sorted_tables
    }


async def run(
    database_url: str, today: date, allowed_host: str | None = None, requests: bool = True
) -> dict[str, int]:
    ensure_local(database_url, allowed_host)  # before connecting: a refused run touches nothing
    engine = make_engine(database_url)
    try:
        async with make_sessionmaker(engine)() as session, session.begin():
            await seed(session, today, requests)
            return await table_counts(session)
    finally:
        await engine.dispose()


def wants_requests(argv: list[str]) -> bool:
    return "--no-requests" not in argv


def main() -> None:
    try:
        counts = asyncio.run(
            run(
                get_settings().database_url,
                date.today(),
                os.environ.get("PAWDESK_SEED_ALLOWED_HOST"),
                wants_requests(sys.argv[1:]),
            )
        )
    except SeedRefused as exc:
        sys.exit(f"seed: {exc}")
    for table, count in counts.items():
        print(f"{table:<22} {count}")


if __name__ == "__main__":
    main()
