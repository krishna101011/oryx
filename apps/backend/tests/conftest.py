"""Shared pytest fixtures.

ANANT_TEST_DB env var, when set to a usable postgres URL, enables the
integration tests marked `requires_db`. They are skipped otherwise so
the unit suite stays runnable anywhere.

Engine lifecycle (Wave F hardening): there is ONE async engine for the whole
test session, with a bounded pool, disposed at session teardown. Previously
each test built its own `create_async_engine` and never disposed it, so the
asyncpg connections accumulated — running the full suite back-to-back
exhausted Postgres. A single shared, bounded, disposed engine fixes that.

Isolation is by unique ids per test (every test mints its own account /
workspace via uuid4), not transaction rollback — the services under test open
and COMMIT their own sessions through the sessionmaker, so a test-owned
nested-transaction would not contain them.
"""
from __future__ import annotations

import os

import pytest


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Auto-skip db-bound tests when ANANT_TEST_DB isn't set."""
    if os.environ.get("ANANT_TEST_DB"):
        return
    skip_db = pytest.mark.skip(reason="ANANT_TEST_DB not set; skipping DB-bound test")
    for item in items:
        if "requires_db" in item.keywords:
            item.add_marker(skip_db)


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def sm():
    """Per-test sessionmaker, centralised here (every DB-bound test inherits it)
    instead of being copied into every file.

    Back-to-back stability comes from a raised Postgres `max_connections` (see
    the ops runbook / pytest notes), not from disposing engines: an async
    teardown fixture and NullPool both deadlocked asyncpg on the portable-PG
    Windows test setup, while this plain sync engine is the configuration that
    reliably passes a full run.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(os.environ["ANANT_TEST_DB"])
    return async_sessionmaker(bind=engine, expire_on_commit=False)
