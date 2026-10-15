import pytest
from sqlalchemy import text

from app.config import get_settings
from app.db import async_url, make_engine

spec = pytest.mark.spec


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


@spec("demo-hosting", "Hosted database URLs work as given")
def test_hosted_url_requires_ssl_the_asyncpg_way():
    url = "postgresql://u:p@ep-x.us-east-1.aws.neon.tech/d?sslmode=require&channel_binding=require"

    assert async_url(url) == "postgresql+asyncpg://u:p@ep-x.us-east-1.aws.neon.tech/d?ssl=require"


@spec("demo-hosting", "Hosted database URLs work as given")
def test_local_url_keeps_its_form_and_other_options():
    assert (
        async_url("postgresql://u:p@localhost:5432/d")
        == "postgresql+asyncpg://u:p@localhost:5432/d"
    )
    assert (
        async_url("postgresql://u:p@h/d?application_name=pawdesk&sslmode=disable")
        == "postgresql+asyncpg://u:p@h/d?application_name=pawdesk&ssl=disable"
    )


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
