"""Two-tier dedupe fingerprint (CR-2)."""
from __future__ import annotations

from datetime import UTC, datetime

from anant.services.dedupe.fingerprint import (
    TIER_BODY_DATE,
    TIER_LINKED,
    compute_fingerprint,
    pick_primary_link,
)


def _fp(**kw):
    defaults = dict(
        sender_domain="example.com",
        subject="Daily Brief",
        primary_link=None,
        received_at=datetime(2026, 6, 7, 9, 0, tzinfo=UTC),
        workspace_tz="UTC",
    )
    defaults.update(kw)
    return compute_fingerprint(**defaults)


def test_linked_tier_picked_when_url_present() -> None:
    fp, tier = _fp(primary_link="https://example.com/article-1")
    assert tier == TIER_LINKED
    assert len(fp) == 64


def test_body_date_tier_picked_when_no_url() -> None:
    fp, tier = _fp(primary_link=None)
    assert tier == TIER_BODY_DATE


def test_body_date_tier_picked_when_url_is_empty() -> None:
    fp, tier = _fp(primary_link="   ")
    assert tier == TIER_BODY_DATE


def test_same_link_same_sender_same_subject_yields_identical_hash() -> None:
    fp1, _ = _fp(primary_link="https://example.com/x")
    fp2, _ = _fp(primary_link="https://example.com/x")
    assert fp1 == fp2


def test_utm_params_do_not_affect_linked_fingerprint() -> None:
    fp1, _ = _fp(primary_link="https://example.com/x")
    fp2, _ = _fp(primary_link="https://example.com/x?utm_source=newsletter")
    assert fp1 == fp2


def test_different_link_yields_different_hash() -> None:
    fp1, _ = _fp(primary_link="https://example.com/x")
    fp2, _ = _fp(primary_link="https://example.com/y")
    assert fp1 != fp2


def test_body_only_same_day_same_sender_same_title_collides() -> None:
    fp1, _ = _fp(received_at=datetime(2026, 6, 7, 6, 0, tzinfo=UTC))
    fp2, _ = _fp(received_at=datetime(2026, 6, 7, 23, 0, tzinfo=UTC))
    assert fp1 == fp2


def test_body_only_different_days_do_not_collide_cr2() -> None:
    """The whole point of CR-2: yesterday and today are different items."""
    fp1, t1 = _fp(received_at=datetime(2026, 6, 6, 9, 0, tzinfo=UTC))
    fp2, t2 = _fp(received_at=datetime(2026, 6, 7, 9, 0, tzinfo=UTC))
    assert t1 == t2 == TIER_BODY_DATE
    assert fp1 != fp2


def test_workspace_tz_affects_date_bucket() -> None:
    """A 23:00 UTC item is 'tomorrow' in Asia/Kolkata; bucket reflects that."""
    received = datetime(2026, 6, 6, 23, 0, tzinfo=UTC)
    fp_utc, _ = _fp(received_at=received, workspace_tz="UTC")
    fp_kolkata, _ = _fp(received_at=received, workspace_tz="Asia/Kolkata")
    # Same item, different workspace tz → different bucket → different hash
    assert fp_utc != fp_kolkata


def test_pick_primary_link_takes_first_nonempty() -> None:
    assert pick_primary_link([]) is None
    assert pick_primary_link(None) is None
    assert (
        pick_primary_link([{"url": "", "anchor": "x"}, {"url": "https://a", "anchor": "A"}])
        == "https://a"
    )


def test_emoji_in_subject_does_not_break_fingerprint() -> None:
    fp1, _ = _fp(primary_link="https://x.test/a", subject="Brief 📈")
    fp2, _ = _fp(primary_link="https://x.test/a", subject="Brief")
    assert fp1 == fp2  # emoji stripped by normalize_title
