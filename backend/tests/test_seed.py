"""Spec: seed-data. Seeding runs inside the rolled-back test session (TRUNCATE is
transactional in Postgres), so these tests leave the test database as they found it."""

from datetime import date, timedelta

import pytest
from sqlalchemy import and_, func, select

import scripts.seed as seed_script
from app.demo import DEMO_TODAY
from app.enums import SizeClass, Vaccine
from app.models import Kennel, Pet, Reservation, VaccineRecord
from scripts.seed import SeedRefused, ensure_local, run, seed, table_counts, wants_requests

spec = pytest.mark.spec
TODAY = date(2027, 3, 1)
# Written by real runs (run-tracing, booking-orchestration), never by seed data.
RUN_TABLES = {
    "traces",
    "spans",
    "booking_step_results",
    "booking_documents",
    "outbound_messages",
}


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


@spec("seed-data", "Seeding refuses non-development databases")
async def test_a_different_remote_host_is_still_refused():
    url = "postgresql://pawdesk:secret@db.prod.example.com:5432/pawdesk"
    with pytest.raises(SeedRefused, match="non-local"):
        await run(url, TODAY, allowed_host="ep-demo.us-east-1.aws.neon.tech")


@spec("seed-data", "Seeding refuses non-development databases")
def test_the_named_remote_host_passes_the_check():
    host = "ep-demo.us-east-1.aws.neon.tech"
    ensure_local(f"postgresql://pawdesk:secret@{host}/pawdesk?sslmode=require", host)
    with pytest.raises(SeedRefused):
        ensure_local(f"postgresql://pawdesk:secret@{host}/pawdesk", "")


REQUEST_TABLES = {"booking_requests", "booking_transitions", "approvals"}


@spec("seed-data", "Seeding can leave out booking requests")
async def test_seed_without_requests_keeps_everything_else(session):
    await seed(session, TODAY)
    full = await table_counts(session)

    await seed(session, TODAY, requests=False)
    bare = await table_counts(session)

    assert all(full[t] > 0 for t in REQUEST_TABLES)
    assert {t: bare[t] for t in REQUEST_TABLES} == dict.fromkeys(REQUEST_TABLES, 0)
    assert {t: c for t, c in bare.items() if t not in REQUEST_TABLES} == {
        t: c for t, c in full.items() if t not in REQUEST_TABLES
    }


@spec("seed-data", "Seeding can leave out booking requests")
def test_requests_are_seeded_unless_left_out():
    assert wants_requests([])
    assert not wants_requests(["--no-requests"])


@spec("seed-data", "Seeded dates are anchored to the demo day")
def test_the_seed_command_anchors_to_the_demo_day(monkeypatch):
    anchors = []

    async def fake_run(database_url, today, allowed_host=None, requests=True):
        anchors.append(today)
        return {}

    monkeypatch.setattr(seed_script, "run", fake_run)
    monkeypatch.setattr(seed_script.sys, "argv", ["seed"])
    seed_script.main()  # whatever the calendar day is
    assert anchors == [DEMO_TODAY]


@spec("seed-data", "Seeded dates are anchored to the demo day")
async def test_records_are_placed_from_the_demo_day(session):
    await seed(session, DEMO_TODAY)
    biscuit = await session.scalar(select(Pet).where(Pet.name == "Biscuit"))
    record = await session.scalar(
        select(VaccineRecord).where(
            VaccineRecord.pet_id == biscuit.id, VaccineRecord.vaccine == Vaccine.BORDETELLA
        )
    )
    assert record.administered_on == DEMO_TODAY - timedelta(days=60)
    assert record.expires_on == DEMO_TODAY + timedelta(days=120)
