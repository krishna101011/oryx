"""core/migration_check.py — the startup check that's supposed to catch a
stale DB loudly, instead of the silent mismatch that caused a real stuck
onboarding flow (dev DB sat 3 migrations behind head with no warning
anywhere)."""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from oryx.core.migration_check import (
    MigrationCheckResult,
    get_current_db_revision,
    get_script_heads,
)


def test_script_heads_reads_the_real_migration_chain() -> None:
    heads = get_script_heads()
    assert isinstance(heads, tuple)
    assert len(heads) >= 1
    assert all(isinstance(h, str) and h for h in heads)


def test_migration_chain_has_no_branch() -> None:
    """More than one head means a branched migration history — itself worth
    flagging, distinct from a merely-stale DB."""
    assert len(get_script_heads()) == 1


def test_up_to_date_true_when_current_matches_the_single_head() -> None:
    result = MigrationCheckResult(current="0030_plan_prices", heads=("0030_plan_prices",))
    assert result.up_to_date is True


def test_up_to_date_false_when_current_is_none() -> None:
    result = MigrationCheckResult(current=None, heads=("0030_plan_prices",))
    assert result.up_to_date is False


def test_up_to_date_false_when_current_is_stale() -> None:
    """The exact real-world shape of the bug this check exists to catch:
    current sitting behind the real head."""
    result = MigrationCheckResult(
        current="0027_catalog_investing_feeds", heads=("0030_plan_prices",)
    )
    assert result.up_to_date is False


def test_up_to_date_false_on_branched_heads() -> None:
    result = MigrationCheckResult(current="abc", heads=("abc", "def"))
    assert result.up_to_date is False


async def test_get_current_db_revision_returns_none_when_alembic_version_table_missing() -> None:
    """A brand-new/uninitialized DB has no alembic_version table at all —
    get_current_db_revision must return None, not raise, so check_and_warn
    never crashes app startup."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        revision = await get_current_db_revision(engine)
        assert revision is None
    finally:
        await engine.dispose()


async def test_get_current_db_revision_reads_the_real_stamped_value() -> None:
    """Proves the happy path against a real (if minimal) alembic_version
    table, independent of Postgres — an in-memory SQLite DB we stamp
    ourselves."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
            )
            await conn.execute(
                text("INSERT INTO alembic_version (version_num) VALUES ('0030_plan_prices')")
            )
        revision = await get_current_db_revision(engine)
        assert revision == "0030_plan_prices"
    finally:
        await engine.dispose()
