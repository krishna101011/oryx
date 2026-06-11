"""Shared pytest fixtures.

ANANT_TEST_DB env var, when set to a usable postgres URL, enables the
integration tests marked `requires_db`. They are skipped otherwise so
the unit suite stays runnable anywhere.
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
