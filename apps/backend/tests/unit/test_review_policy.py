"""Phase 5 Wave C — review-policy + note-requirement unit guards.

These prove the two service-layer rules fire WITHOUT a database:
  - Refinement 1: reject / request-changes need a non-empty note (HTTP 400).
  - §15.3 self-approval policy: the pure decision function, every branch.

Mirrors tests/unit/test_analyst_review.py's exploding-sessionmaker pattern —
an empty note must short-circuit before any DB work.
"""
from __future__ import annotations

import uuid

import pytest

from oryx.core.errors import BadRequestError
from oryx.services.drafts.service import (
    DraftService,
    _require_note,
    _self_approval_allowed,
)

# ---------------- note requirement (Refinement 1) ----------------


def test_require_note_rejects_empty() -> None:
    with pytest.raises(BadRequestError):
        _require_note("")


def test_require_note_rejects_whitespace() -> None:
    with pytest.raises(BadRequestError):
        _require_note("   \n\t ")


def test_require_note_rejects_none() -> None:
    with pytest.raises(BadRequestError):
        _require_note(None)


def test_require_note_accepts_and_trims() -> None:
    assert _require_note("  needs a tighter lede  ") == "needs a tighter lede"


# ---------------- self-approval policy (§15.3) ----------------


def test_policy_other_account_always_allowed() -> None:
    # Reviewing someone else's draft is never restricted, even under 'strict'.
    assert _self_approval_allowed(
        is_platform_admin=False, strictness="strict", is_self=False
    )


def test_policy_self_loose_allowed() -> None:
    assert _self_approval_allowed(
        is_platform_admin=False, strictness="loose", is_self=True
    )


def test_policy_self_balanced_blocked() -> None:
    assert not _self_approval_allowed(
        is_platform_admin=False, strictness="balanced", is_self=True
    )


def test_policy_self_strict_blocked() -> None:
    assert not _self_approval_allowed(
        is_platform_admin=False, strictness="strict", is_self=True
    )


def test_policy_platform_admin_overrides_strict() -> None:
    # Platform admin may self-approve regardless of policy.
    assert _self_approval_allowed(
        is_platform_admin=True, strictness="strict", is_self=True
    )


# ---------------- empty note short-circuits before DB ----------------


def _exploding_sessionmaker():
    def _sm():
        raise AssertionError("DB must not be touched when the note is empty")

    return _sm


@pytest.mark.asyncio
async def test_reject_empty_note_blocks_before_db() -> None:
    svc = DraftService(_exploding_sessionmaker())
    with pytest.raises(BadRequestError):
        await svc.reject_draft(
            draft_id=uuid.uuid4(),
            account_id=uuid.uuid4(),
            workspace_id=uuid.uuid4(),
            note="   ",
        )


@pytest.mark.asyncio
async def test_request_changes_empty_note_blocks_before_db() -> None:
    svc = DraftService(_exploding_sessionmaker())
    with pytest.raises(BadRequestError):
        await svc.request_changes(
            draft_id=uuid.uuid4(),
            account_id=uuid.uuid4(),
            workspace_id=uuid.uuid4(),
            note="",
        )
