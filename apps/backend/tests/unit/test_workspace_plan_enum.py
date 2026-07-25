"""Workspace.plan widening (billing foundation wave) touches three
independent code sites that must agree: core/models.py's SQLAlchemy Enum,
shared/types.py's pydantic Literal, and packages/shared-types/src/workspaces.ts's
TS union. `pnpm drift:check` only verifies types.py PARSES, not that its
Literals match the TS or the DB (see .claude/skills/oryx-architect/SKILL.md's
"ENUM-WIDENING DRIFT IS SILENT" entry — the Phase 6 Wave B incident this
project already hit once with ActivityType). This test is the by-hand check
that lesson calls for.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import get_args

from oryx.core.models import Workspace
from oryx.shared.types import WorkspacePlan

_REPO_ROOT = Path(__file__).resolve().parents[4]
_TS_FILE = _REPO_ROOT / "packages" / "shared-types" / "src" / "workspaces.ts"

EXPECTED = {"glimpse", "focus", "clarity", "vision"}


def test_sqlalchemy_enum_matches_expected_tiers() -> None:
    column_type = Workspace.__table__.columns["plan"].type
    assert set(column_type.enums) == EXPECTED


def test_pydantic_literal_matches_expected_tiers() -> None:
    assert set(get_args(WorkspacePlan)) == EXPECTED


def test_ts_union_matches_expected_tiers() -> None:
    text = _TS_FILE.read_text(encoding="utf-8")
    match = re.search(r"export type WorkspacePlan = ([^;]+);", text)
    assert match is not None, "WorkspacePlan type not found in workspaces.ts"
    values = {v.strip().strip("'\"") for v in match.group(1).split("|")}
    assert values == EXPECTED


def test_all_three_sites_agree_with_each_other() -> None:
    """Belt-and-suspenders: even if EXPECTED itself were wrong, this proves
    the three sites can't silently drift from one another."""
    sqlalchemy_values = set(Workspace.__table__.columns["plan"].type.enums)
    pydantic_values = set(get_args(WorkspacePlan))
    text = _TS_FILE.read_text(encoding="utf-8")
    match = re.search(r"export type WorkspacePlan = ([^;]+);", text)
    assert match is not None
    ts_values = {v.strip().strip("'\"") for v in match.group(1).split("|")}

    assert sqlalchemy_values == pydantic_values == ts_values
