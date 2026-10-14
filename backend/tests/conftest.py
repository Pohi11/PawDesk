"""Shared fixtures: a migrated test database and per-test transactional isolation.

Tests that need the database take the `session` fixture. Everything a test writes,
including commits, is rolled back when the test ends.
"""

import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import make_engine, make_sessionmaker
from app.enums import Service, Species, Vaccine
from app.models import (
    Base,
    Facility,
    Kennel,
    Owner,
    Pet,
    Trace,
    VaccineRecord,
    VaccineRule,
)
from app.tracing import Tracer

# Separate checkouts (worktrees) running at the same time each need their own database,
# because every session starts by migrating it down and up.
TEST_DB_NAME = os.environ.get("PAWDESK_TEST_DB", "pawdesk_test")
if not re.fullmatch(r"[a-z_][a-z0-9_]*", TEST_DB_NAME):
    raise ValueError(f"PAWDESK_TEST_DB must be a plain lowercase identifier, got {TEST_DB_NAME!r}")
BACKEND_DIR = Path(__file__).resolve().parents[1]


def pytest_collection_modifyitems(items):
    """Copy each `@pytest.mark.spec(capability, requirement)` into the test's user properties.

    pytest writes user properties into JUnit XML (`--junitxml`), so a test report can be
    joined back to the OpenSpec requirement each test verifies (decision record 0004).
    """
    for item in items:
        for marker in item.iter_markers(name="spec"):
            if len(marker.args) != 2 or not all(isinstance(a, str) and a for a in marker.args):
                raise pytest.UsageError(
                    f"{item.nodeid}: use @pytest.mark.spec('<capability>', '<requirement>')"
                )
            capability, requirement = marker.args
            item.user_properties.append(("spec", f"{capability}: {requirement}"))


def _test_database_url() -> str:
    url = make_url(get_settings().database_url).set(database=TEST_DB_NAME)
    return url.render_as_string(hide_password=False)


def _ensure_test_database_exists() -> None:
    # CREATE DATABASE can't run inside a transaction, hence autocommit, and it has to run
    # from a connection to some *other* database (the default `postgres` one).
    admin_url = make_url(get_settings().database_url).set(
        database="postgres", drivername="postgresql"
    )
    with psycopg.connect(admin_url.render_as_string(hide_password=False), autocommit=True) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DB_NAME,)
        ).fetchone()
        if not exists:
            conn.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')


@pytest.fixture(scope="session")
def test_database_url() -> str:
    """Create the test database if needed and run every migration down, then up.

    Running the downgrade path on each session catches broken downgrades early.
    """
    _ensure_test_database_exists()
    url = _test_database_url()
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    return url


@pytest.fixture(scope="session")
async def engine(test_database_url):
    engine = make_engine(test_database_url)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session(engine):
    """A session inside an outer transaction that is always rolled back.

    join_transaction_mode="create_savepoint" turns the code-under-test's commit() into a
    savepoint release, so code can commit normally without anything reaching the database.
    """
    async with engine.connect() as conn:
        outer = await conn.begin()
        session = AsyncSession(
            bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        try:
            yield session
        finally:
            await session.close()
            await outer.rollback()


@pytest.fixture
async def tracer(engine):
    """A Tracer on the test database. Its writes are committed (that's the point of
    tracing), so it remembers the traces it created and deletes them afterward."""
    sessions = make_sessionmaker(engine)
    created: list = []

    class CleaningTracer(Tracer):
        async def _insert(self, row):
            row_id = await super()._insert(row)
            if isinstance(row, Trace):
                created.append(row_id)
            return row_id

    yield CleaningTracer(sessions)

    if created:
        async with sessions() as cleanup, cleanup.begin():
            await cleanup.execute(
                text("DELETE FROM spans WHERE trace_id = ANY(:ids)"), {"ids": created}
            )
            await cleanup.execute(text("DELETE FROM traces WHERE id = ANY(:ids)"), {"ids": created})


@pytest.fixture
async def committed(engine):
    """A sessionmaker whose commits are real, for work that spans several sessions and
    connections (the orchestrator, the command line). Every table is emptied afterward."""
    sessions = make_sessionmaker(engine)
    yield sessions
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    async with sessions() as cleanup, cleanup.begin():
        await cleanup.execute(text(f"TRUNCATE {tables} CASCADE"))


@dataclass
class Desk:
    facility_id: object
    owner_id: object
    biscuit_id: object
    olive_id: object
    kennel_id: object


@pytest.fixture
async def desk(committed) -> Desk:
    """A facility with one owner, Biscuit (medium dog) and Olive (cat), one medium kennel,
    and Biscuit's records on file: rabies and DHPP, but no bordetella."""
    async with committed() as s:
        facility = Facility(name="Test Lodge", timezone="America/Chicago")
        owner = Owner(full_name="Test Owner", email="orchestrator@example.test")
        s.add_all([facility, owner])
        await s.flush()
        biscuit = Pet(owner_id=owner.id, name="Biscuit", species=Species.DOG, weight_lb=35)
        olive = Pet(owner_id=owner.id, name="Olive", species=Species.CAT, weight_lb=9)
        kennel = Kennel(facility_id=facility.id, name="M1", size_class="medium")
        s.add_all([biscuit, olive, kennel])
        await s.flush()
        s.add_all(
            [
                VaccineRule(
                    facility_id=facility.id, service=service, species=Species.DOG, vaccine=v
                )
                for service, vaccines in {
                    Service.BOARDING: [Vaccine.RABIES, Vaccine.DHPP, Vaccine.BORDETELLA],
                    Service.GROOMING: [Vaccine.RABIES],
                }.items()
                for v in vaccines
            ]
            + [
                VaccineRecord(
                    pet_id=biscuit.id,
                    vaccine=v,
                    administered_on=date(2026, 4, 1),
                    expires_on=date(2028, 4, 1),
                )
                for v in (Vaccine.RABIES, Vaccine.DHPP)
            ]
        )
        await s.commit()
        return Desk(facility.id, owner.id, biscuit.id, olive.id, kennel.id)
