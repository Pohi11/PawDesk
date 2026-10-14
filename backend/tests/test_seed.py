"""Spec: seed-data. Seeding runs inside the rolled-back test session (TRUNCATE is
transactional in Postgres), so these tests leave the test database as they found it."""

from datetime import date

import pytest
from sqlalchemy import and_, func, select

from app.enums import SizeClass
from app.models import Kennel, Reservation, VaccineRecord
from scripts.seed import SeedRefused, run, seed, table_counts

spec = pytest.mark.spec
TODAY = date(2027, 3, 1)
# Written by real runs (run-tracing, booking-orchestration), never by seed data.
RUN_TABLES = {"traces", "spans", "booking_step_results", "booking_documents"}


@spec("seed-data", "Seeding loads a known synthetic dataset")
async def test_seed_populates_every_table(session):
    await seed(session, TODAY)

    counts = await table_counts(session)
    kennel_classes = set(await session.scalars(select(Kennel.size_class).distinct()))

    empty = sorted(n for n, c in counts.items() if c == 0 and n not in RUN_TABLES)
    assert empty == []
    assert kennel_classes == set(SizeClass)


@spec("seed-data", "Seeding loads a known synthetic dataset")
async def test_seed_covers_vaccine_edge_cases(session):
    await seed(session, TODAY)

    expired = await session.scalar(select(func.count()).where(VaccineRecord.expires_on < TODAY))
    no_expiry = await session.scalar(select(func.count()).where(VaccineRecord.expires_on.is_(None)))
    expires_mid_stay = await session.scalar(
        select(func.count())
        .select_from(VaccineRecord)
        .join(
            Reservation,
            and_(
                Reservation.pet_id == VaccineRecord.pet_id,
                Reservation.start_date > TODAY,
                VaccineRecord.expires_on >= Reservation.start_date,
                VaccineRecord.expires_on < Reservation.end_date,
            ),
        )
    )

    assert expired >= 1
    assert no_expiry >= 1
    assert expires_mid_stay >= 1


@spec("seed-data", "Seeding is repeatable")
async def test_running_seed_twice_gives_the_same_counts(session):
    await seed(session, TODAY)
    first = await table_counts(session)

    await seed(session, TODAY)

    assert await table_counts(session) == first


@spec("seed-data", "Seeding refuses non-development databases")
@pytest.mark.parametrize(
    "url",
    [
        "postgresql://pawdesk:secret@db.prod.example.com:5432/pawdesk",
        "postgresql://pawdesk:secret@10.0.0.12:5432/pawdesk",
    ],
)
async def test_remote_database_is_refused_before_connecting(url):
    # If run() tried to connect, this would fail with a connection error instead.
    with pytest.raises(SeedRefused, match="non-local"):
        await run(url, TODAY)
