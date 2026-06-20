"""Manual ingest policy — deterministic external_id + rate limiting (CR-8)."""
from __future__ import annotations

import uuid

from oryx.services.intake.admin_router import (
    _manual_external_id,
    _manual_ingest_hits,
    _manual_ingest_rate_ok,
    _ManualIngestBody,
)


def _body(**overrides: object) -> _ManualIngestBody:
    kwargs: dict = dict(
        workspace_id=str(uuid.uuid4()),
        title="A headline",
        url="https://example.com/article?utm_source=x",
        body_text=None,
        sender=None,
    )
    kwargs.update(overrides)
    return _ManualIngestBody(**kwargs)


def test_same_url_resubmission_yields_same_external_id() -> None:
    # Tracking params are canonicalized away → provider-key dedupe catches
    # the resubmission instead of creating a second raw record.
    a = _manual_external_id(_body(url="https://example.com/article?utm_source=x"))
    b = _manual_external_id(_body(url="https://example.com/article"))
    assert a == b


def test_body_only_submission_is_deterministic_on_title_and_body() -> None:
    one = _manual_external_id(_body(url=None, body_text="text", title="T"))
    two = _manual_external_id(_body(url=None, body_text="text", title="T"))
    other = _manual_external_id(_body(url=None, body_text="different", title="T"))
    assert one == two
    assert one != other


def test_rate_limit_blocks_after_window_fills() -> None:
    account = f"acct-{uuid.uuid4().hex}"
    for _ in range(5):
        assert _manual_ingest_rate_ok(account, limit=5)
    assert not _manual_ingest_rate_ok(account, limit=5)


def test_rate_limit_is_per_account() -> None:
    a, b = f"a-{uuid.uuid4().hex}", f"b-{uuid.uuid4().hex}"
    for _ in range(3):
        assert _manual_ingest_rate_ok(a, limit=3)
    assert not _manual_ingest_rate_ok(a, limit=3)
    assert _manual_ingest_rate_ok(b, limit=3)
    _manual_ingest_hits.clear()
