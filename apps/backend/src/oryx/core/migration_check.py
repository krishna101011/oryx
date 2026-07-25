"""Startup-time check: is this database actually at the latest migration
head? Runs on every app startup (see main.py's _lifespan) so a stale DB
shows up immediately and loudly in the terminal, not silently — the exact
failure mode that let the real dev DB sit 3 migrations behind head
(0027 vs head 0030) while the app kept running against mismatched schema,
diagnosed the hard way via a stuck onboarding flow.

Non-fatal by design: this is a loud warning, not a startup abort. Aborting
would be too aggressive for local dev (a momentarily-behind DB during a
rebase, or a fresh checkout before the first `alembic upgrade head`, should
not brick `uvicorn --reload`) and is actively wrong in test contexts where
a separate fixture manages migrations on its own schedule.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from oryx.core.logging import get_logger

logger = get_logger(__name__)

_ALEMBIC_DIR = Path(__file__).resolve().parents[3] / "alembic"


@dataclass(frozen=True)
class MigrationCheckResult:
    current: str | None
    heads: tuple[str, ...]

    @property
    def up_to_date(self) -> bool:
        return self.current is not None and set(self.heads) == {self.current}


def get_script_heads() -> tuple[str, ...]:
    """Reads the migration chain's head revision(s) straight off disk — no
    DB connection needed. More than one head means a branched migration
    history, which is itself worth flagging."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config()
    cfg.set_main_option("script_location", str(_ALEMBIC_DIR))
    script = ScriptDirectory.from_config(cfg)
    return tuple(script.get_heads())


async def get_current_db_revision(engine: AsyncEngine) -> str | None:
    """None means either a brand-new DB (alembic_version doesn't exist yet)
    or the table is unexpectedly empty — both are real "not at head" states,
    not errors, so this never raises."""
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            row = result.first()
            return row[0] if row is not None else None
    except Exception:
        # Best-effort startup diagnostic — must never crash the app.
        return None


def _print_banner(result: MigrationCheckResult) -> None:
    """A loud, human-scannable banner on stderr — deliberately NOT just a
    structured JSON log line, which is easy to miss scrolling past in a busy
    terminal. logger.warning() below still fires for anything that parses
    the JSON log stream (e.g. a log aggregator)."""
    lines = [
        "",
        "!" * 78,
        "! MIGRATION STATE WARNING — this database is NOT at the latest schema head",
        f"!   current revision : {result.current!r}",
        f"!   latest head(s)   : {result.heads!r}",
        "!   Fix: uv run python -m alembic upgrade head",
        "!" * 78,
        "",
    ]
    print("\n".join(lines), file=sys.stderr, flush=True)


async def check_and_warn(engine: AsyncEngine) -> MigrationCheckResult:
    """Call once at app startup. Always returns a result; never raises."""
    heads = get_script_heads()
    current = await get_current_db_revision(engine)
    result = MigrationCheckResult(current=current, heads=heads)

    if result.up_to_date:
        logger.info(
            "migration.up_to_date",
            extra={"current": result.current, "heads": list(result.heads)},
        )
    else:
        logger.warning(
            "migration.stale_database",
            extra={"current": result.current, "heads": list(result.heads)},
        )
        _print_banner(result)

    return result
