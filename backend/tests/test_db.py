import pytest
from sqlalchemy import text

from app.config import get_settings
from app.db import async_url, make_engine


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://u:p@h:5432/d",
        "postgres://u:p@h:5432/d",
        "postgresql+asyncpg://u:p@h:5432/d",
    ],
)
def test_async_url_uses_asyncpg_driver(url):
    assert async_url(url) == "postgresql+asyncpg://u:p@h:5432/d"


def test_async_url_rejects_other_databases():
    with pytest.raises(ValueError):
        async_url("mysql://u:p@h/d")


async def test_engine_executes_select_1():
    engine = make_engine(get_settings().database_url)
    try:
        async with engine.connect() as conn:
            assert (await conn.execute(text("SELECT 1"))).scalar_one() == 1
    finally:
        await engine.dispose()
