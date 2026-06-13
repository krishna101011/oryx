"""VerificationEngine — the §14.3 outcome rules, exhaustively."""
from __future__ import annotations

import pytest

from anant.services.verification.engine import ENGINE_VERSION, VerificationEngine
from anant.services.verification.models import EvidenceLinkInput


def _link(relationship: str, evidence_type: str = "corroboration", strength: float = 0.7):
    return EvidenceLinkInput(
        relationship=relationship, strength=strength, evidence_type=evidence_type
    )


PRIMARY = _link("supports", "primary_source")
SUPPORT = _link("supports", "corroboration")
CONTRA = _link("contradicts", "contradiction", 0.0)


@pytest.fixture
def engine() -> VerificationEngine:
    return VerificationEngine()


def test_engine_version_is_one() -> None:
    assert ENGINE_VERSION == 1
    assert VerificationEngine.version == 1


def test_unclassified_is_always_unverifiable(engine: VerificationEngine) -> None:
    assert engine.determine_outcome("unclassified", []) == "unverifiable"
    assert engine.determine_outcome("unclassified", [PRIMARY, SUPPORT]) == "unverifiable"


@pytest.mark.parametrize("etype", ["opinion", "rumor", "speculation"])
def test_low_types_never_verified(etype: str, engine: VerificationEngine) -> None:
    # No contradiction -> unverified (NOT verified, even with primary support).
    assert engine.determine_outcome(etype, [PRIMARY, SUPPORT]) == "unverified"
    assert engine.determine_outcome(etype, []) == "unverified"
    # Any contradiction -> contested.
    assert engine.determine_outcome(etype, [CONTRA]) == "contested"
    assert engine.determine_outcome(etype, [PRIMARY, CONTRA]) == "contested"


def test_fact_requires_primary_support(engine: VerificationEngine) -> None:
    # Non-primary support is not enough for a fact.
    assert engine.determine_outcome("fact", [SUPPORT]) == "unverified"
    assert engine.determine_outcome("fact", []) == "unverified"
    # Primary support, no contradiction -> verified.
    assert engine.determine_outcome("fact", [PRIMARY]) == "verified"
    # Primary support + contradiction -> contested.
    assert engine.determine_outcome("fact", [PRIMARY, CONTRA]) == "contested"


def test_claim_requires_any_support(engine: VerificationEngine) -> None:
    assert engine.determine_outcome("claim", []) == "unverified"
    # A contextualizes-only link is not support.
    assert engine.determine_outcome("claim", [_link("contextualizes", "context")]) == "unverified"
    # Any supporting link, no contradiction -> verified.
    assert engine.determine_outcome("claim", [SUPPORT]) == "verified"
    assert engine.determine_outcome("claim", [PRIMARY]) == "verified"
    # Support + contradiction -> contested.
    assert engine.determine_outcome("claim", [SUPPORT, CONTRA]) == "contested"


def test_contextualizes_does_not_count_as_support(engine: VerificationEngine) -> None:
    ctx = _link("contextualizes", "context")
    assert engine.determine_outcome("claim", [ctx]) == "unverified"
    assert engine.determine_outcome("fact", [ctx]) == "unverified"
