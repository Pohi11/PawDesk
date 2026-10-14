"""Proves the `session` fixture rolls back everything a test does, even after commit().

The two tests run in file order: the first commits a table and a row, the second checks
that neither survived. Postgres DDL is transactional, so even CREATE TABLE rolls back.
"""

from sqlalchemy import text


async def test_commit_inside_a_test(session):
    await session.execute(text("CREATE TABLE isolation_probe (id int)"))
    await session.execute(text("INSERT INTO isolation_probe VALUES (1)"))
    await session.commit()

    assert (await session.execute(text("SELECT count(*) FROM isolation_probe"))).scalar_one() == 1


async def test_previous_commit_was_rolled_back(session):
    exists = await session.execute(text("SELECT to_regclass('isolation_probe')"))

    assert exists.scalar_one() is None
