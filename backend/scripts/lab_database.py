"""Throwaway local databases for the comparison lab and the end-to-end tests: created if
needed, migrated from scratch, and seeded as of a chosen day. Local hosts only."""

import asyncio
from datetime import date
from pathlib import Path

import psycopg
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url

from scripts.seed import ensure_local
from scripts.seed import run as seed_run

BACKEND = Path(__file__).resolve().parents[1]


def database_url(base_url: str, name: str) -> str:
    """A database next to the configured one, refusing anything but a local host."""
    ensure_local(base_url)
    return make_url(base_url).set(database=name).render_as_string(hide_password=False)


def prepare(url: str, today: date) -> None:
    """Create the database if needed, migrate it from scratch, and seed it as of `today`."""
    ensure_local(url)
    admin = make_url(url).set(database="postgres", drivername="postgresql")
    name = make_url(url).database
    with psycopg.connect(admin.render_as_string(hide_password=False), autocommit=True) as conn:
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone()
        if not exists:
            conn.execute(f'CREATE DATABASE "{name}"')
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    asyncio.run(seed_run(url, today))
