"""Packet readiness gate pure logic (Wave E)."""
from __future__ import annotations

from anant.services.research.models import ObjectReadinessInput, evaluate_readiness


def _obj(oid: str, status: str) -> ObjectReadinessInput:
    return ObjectReadinessInput(id=oid, headline=f"H-{oid}", verification_status=status)


def test_empty_packet_is_ready() -> None:
    r = evaluate_readiness([], set())
    assert r.is_ready is True
    assert r.blockers == []


def test_all_verified_is_ready() -> None:
    r = evaluate_readiness([_obj("a", "verified"), _obj("b", "verified")], set())
    assert r.is_ready is True


def test_unverified_is_ready() -> None:
    # 'unverified' is not a blocker — only rejected / unacknowledged-contested.
    r = evaluate_readiness([_obj("a", "unverified")], set())
    assert r.is_ready is True


def test_analyst_approved_is_ready() -> None:
    r = evaluate_readiness([_obj("a", "analyst_approved")], set())
    assert r.is_ready is True


def test_rejected_blocks() -> None:
    r = evaluate_readiness([_obj("a", "analyst_rejected")], set())
    assert r.is_ready is False
    assert r.blockers == ["Object 'H-a' has been rejected"]


def test_contested_unacknowledged_blocks() -> None:
    r = evaluate_readiness([_obj("a", "contested")], set())
    assert r.is_ready is False
    assert "unacknowledged conflict" in r.blockers[0]


def test_contested_acknowledged_is_ready() -> None:
    r = evaluate_readiness([_obj("a", "contested")], {"a"})
    assert r.is_ready is True


def test_contested_acknowledged_other_id_still_blocks() -> None:
    r = evaluate_readiness([_obj("a", "contested")], {"b"})
    assert r.is_ready is False


def test_multiple_blockers_accumulate() -> None:
    r = evaluate_readiness(
        [_obj("a", "analyst_rejected"), _obj("b", "contested")], set()
    )
    assert r.is_ready is False
    assert len(r.blockers) == 2


def test_mixed_clean_and_acknowledged_is_ready() -> None:
    r = evaluate_readiness(
        [
            _obj("a", "verified"),
            _obj("b", "contested"),
            _obj("c", "analyst_approved"),
        ],
        {"b"},
    )
    assert r.is_ready is True


def test_rejected_blocks_even_if_acknowledged() -> None:
    # Acknowledgement only clears contested, not a hard rejection.
    r = evaluate_readiness([_obj("a", "analyst_rejected")], {"a"})
    assert r.is_ready is False


def test_two_contested_one_acknowledged_still_blocks() -> None:
    r = evaluate_readiness(
        [_obj("a", "contested"), _obj("b", "contested")], {"a"}
    )
    assert r.is_ready is False
    assert len(r.blockers) == 1  # only b remains unacknowledged


def test_all_contested_all_acknowledged_ready() -> None:
    r = evaluate_readiness(
        [_obj("a", "contested"), _obj("b", "contested")], {"a", "b"}
    )
    assert r.is_ready is True


def test_blocker_message_includes_headline() -> None:
    r = evaluate_readiness([_obj("x", "analyst_rejected")], set())
    assert "H-x" in r.blockers[0]


def test_verified_with_acknowledgement_noise_ready() -> None:
    # Acknowledging an id that isn't contested is harmless.
    r = evaluate_readiness([_obj("a", "verified")], {"zzz"})
    assert r.is_ready is True


def test_unverified_and_verified_mix_ready() -> None:
    r = evaluate_readiness(
        [_obj("a", "unverified"), _obj("b", "verified")], set()
    )
    assert r.is_ready is True
