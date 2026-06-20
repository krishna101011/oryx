"""Analyst-review note enforcement + outcome maps (Wave D).

The not-empty note rule is enforced in the SERVICE layer (HTTP 400), before
any DB work — these tests prove it fires without a usable sessionmaker.
"""
from __future__ import annotations

import uuid

import pytest

from oryx.core.errors import BadRequestError
from oryx.services.review.service import (
    _CONFLICT_OUTCOME,
    _OBJECT_STATUS,
    ReviewService,
    _require_note,
)


def test_require_note_rejects_empty() -> None:
    with pytest.raises(BadRequestError):
        _require_note("")


def test_require_note_rejects_whitespace() -> None:
    with pytest.raises(BadRequestError):
        _require_note("   \n\t ")


def test_require_note_accepts_text() -> None:
    _require_note("because the filing supersedes the rumor")  # no raise


def _exploding_sessionmaker():
    def _sm():
        raise AssertionError("DB must not be touched when the note is empty")

    return _sm


@pytest.mark.asyncio
async def test_resolve_conflict_empty_note_blocks_before_db() -> None:
    svc = ReviewService(_exploding_sessionmaker())
    with pytest.raises(BadRequestError):
        await svc.resolve_conflict(
            conflict_id=uuid.uuid4(),
            workspace_id=uuid.uuid4(),
            account_id=uuid.uuid4(),
            outcome="a_wins",
            note="",
        )


@pytest.mark.asyncio
async def test_review_claim_empty_note_blocks_before_db() -> None:
    svc = ReviewService(_exploding_sessionmaker())
    with pytest.raises(BadRequestError):
        await svc.review_claim(
            claim_id=uuid.uuid4(),
            workspace_id=uuid.uuid4(),
            account_id=uuid.uuid4(),
            outcome="approved",
            note="   ",
        )


@pytest.mark.asyncio
async def test_review_object_empty_note_blocks_before_db() -> None:
    svc = ReviewService(_exploding_sessionmaker())
    with pytest.raises(BadRequestError):
        await svc.review_object(
            object_id=uuid.uuid4(),
            workspace_id=uuid.uuid4(),
            account_id=uuid.uuid4(),
            outcome="flagged",
            note="",
        )


def test_conflict_outcome_map() -> None:
    assert _CONFLICT_OUTCOME["a_wins"] == ("resolved_a_wins", "conflict_resolved_a")
    assert _CONFLICT_OUTCOME["b_wins"] == ("resolved_b_wins", "conflict_resolved_b")
    assert _CONFLICT_OUTCOME["inconclusive"] == (
        "resolved_inconclusive",
        "conflict_inconclusive",
    )


def test_object_status_map() -> None:
    assert _OBJECT_STATUS["approved"] == "analyst_approved"
    assert _OBJECT_STATUS["rejected"] == "analyst_rejected"
    assert _OBJECT_STATUS["flagged"] is None  # advisory, no status change
