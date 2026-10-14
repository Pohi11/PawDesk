from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings


def async_url(url: str) -> str:
    """Point a plain postgresql:// URL at SQLAlchemy's asyncpg driver.

    .env keeps the driver-neutral form so the same value works for psql and other tools.
    """
    for prefix in ("postgresql+asyncpg://", "postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+asyncpg://" + url.removeprefix(prefix)
    raise ValueError("DATABASE_URL must start with postgresql://")


def make_engine(url: str) -> AsyncEngine:
    # pool_pre_ping checks a pooled connection before use, so a Postgres restart doesn't
    # surface as an error on the first request afterward.
    return create_async_engine(async_url(url), pool_pre_ping=True)


def make_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    # expire_on_commit=False: after commit, objects keep their loaded values instead of
    # needing a refresh, which in async code would be an implicit query that can't run.
    return async_sessionmaker(engine, expire_on_commit=False)


@lru_cache
def get_engine() -> AsyncEngine:
    return make_engine(get_settings().database_url)


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return make_sessionmaker(get_engine())
