"""Shared fixtures.

Database-backed tests need a *dedicated* test database (they drop and recreate the public
schema) -- never point this at the dev database:

    $env:FALCON_TEST_DATABASE_URL = "postgresql://falcon:falcon@localhost:5432/falcon_test"

Without it, DB tests are skipped and the rest of the suite still runs.
"""

from __future__ import annotations

import os

import pytest

from engine.database import Database

TEST_DB_URL = os.environ.get("FALCON_TEST_DATABASE_URL")

requires_db = pytest.mark.skipif(not TEST_DB_URL, reason="FALCON_TEST_DATABASE_URL not set")


@pytest.fixture
async def db() -> Database:
    """A connected Database on a freshly wiped + migrated schema."""
    assert TEST_DB_URL
    database = Database(TEST_DB_URL)
    await database.connect()
    async with database.pool.acquire() as conn:
        await conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    await database.migrate()
    try:
        yield database
    finally:
        await database.close()
