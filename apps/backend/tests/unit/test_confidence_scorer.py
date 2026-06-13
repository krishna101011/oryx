"""ConfidenceScorer — §14.4 / ADR-027 arithmetic, exhaustively."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from anant.services.verification.models import EvidenceLinkInput
from anant.services.verification.scorer import (
    CEILINGS,
    EVIDENCE_STRENGTH_WEIGHTS,
    SCORING_VERSION,
    W_CROSS_REF,
    W_EVIDENCE_STRENGTH,
    W_PRIMARY_SOURCE,
    W_RECENCY,
    W_SOURCE_TRUST,
    W_SPECIFICITY,
    ConfidenceScorer,
    _evidence_strength_score,
    _specificity_score,
)

NOW = datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC)


def _link(relationship: str, evidence_type: str, strength: float = 0.8):
    return EvidenceLinkInput(
        relationship=relationship, strength=strength, evidence_type=evidence_type
    )


@pytest.fixture
def scorer() -> ConfidenceScorer:
    return ConfidenceScorer()


def test_scoring_version_is_one() -> None:
    assert SCORING_VERSION == 1
    assert ConfidenceScorer.version == 1


def test_weights_sum_to_exactly_one() -> None:
    total = (
        W_SOURCE_TRUST + W_CROSS_REF + W_EVIDENCE_STRENGTH
        + W_RECENCY + W_SPECIFICITY + W_PRIMARY_SOURCE
    )
    assert total == pytest.approx(1.0)


def test_unclassified_returns_none(scorer: ConfidenceScorer) -> None:
    result = scorer.score(
        epistemic_type="unclassified", accuracy_rate=0.9,
        links=[_link("supports", "primary_source")],
        received_at=NOW, object_text="x y z w", now=NOW,
    )
    assert result.confidence_score is None
    # Factors are still computed for observability.
    assert result.factors.cross_reference_count == 1


@pytest.mark.parametrize(
    ("etype", "ceiling"),
    [("fact", 1.0), ("claim", 0.85), ("speculation", 0.60), ("rumor", 0.40), ("opinion", 0.30)],
)
def test_epistemic_ceiling_caps_the_composite(
    etype: str, ceiling: float, scorer: ConfidenceScorer
) -> None:
    # Max-out every factor: 3 primary supporting links, perfect trust,
    # fresh, specific. Composite would be ~1.0; the ceiling must cap it.
    links = [_link("supports", "primary_source", 1.0) for _ in range(3)]
    result = scorer.score(
        epistemic_type=etype, accuracy_rate=1.0, links=links,
        received_at=NOW, object_text="a b c d e", now=NOW,
    )
    assert result.confidence_score is not None
    assert result.confidence_score == pytest.approx(ceiling)
    assert CEILINGS[etype] == ceiling


def test_zero_cross_references_renormalizes_not_collapses(scorer: ConfidenceScorer) -> None:
    # A single non-supporting (context) link: cross_reference_count == 0.
    # Score must NOT collapse to ~0; the remaining 5 factors renormalize.
    links = [_link("contextualizes", "context", 0.9)]
    result = scorer.score(
        epistemic_type="claim", accuracy_rate=1.0, links=links,
        received_at=NOW, object_text="a b c d e", now=NOW,
    )
    assert result.factors.cross_reference_count == 0
    # Hand-compute: factors with weights renormalized over 0.75.
    # source_trust=1.0(.25), evidence: context weight 0.3, strength 0.9 -> 0.9(.20),
    # recency=1.0(.10), specificity=1.0(.10), primary=0.0(.10)
    num = 1.0 * 0.25 + 0.9 * 0.20 + 1.0 * 0.10 + 1.0 * 0.10 + 0.0 * 0.10
    expected = num / 0.75  # 0.6300/0.75 = 0.84
    assert result.confidence_score == pytest.approx(min(expected, 0.85))
    assert result.confidence_score > 0.5  # decidedly not collapsed


def test_cross_reference_count_score_mapping(scorer: ConfidenceScorer) -> None:
    def score_for(n: int) -> float:
        links = [_link("supports", "secondary_source", 0.0) for _ in range(n)]
        r = scorer.score(
            epistemic_type="claim", accuracy_rate=0.0, links=links,
            received_at=NOW, object_text=None, now=NOW,
        )
        return r.factors.cross_reference_count_score

    assert score_for(1) == pytest.approx(0.4)
    assert score_for(2) == pytest.approx(0.7)
    assert score_for(3) == pytest.approx(1.0)
    assert score_for(5) == pytest.approx(1.0)


def test_specificity_factor() -> None:
    assert _specificity_score(None) == 0.2
    assert _specificity_score("  ") == 0.2
    assert _specificity_score("a b c") == 0.5         # <= 3 tokens
    assert _specificity_score("a b c d") == 1.0       # > 3 tokens


def test_evidence_strength_weighted_mean_excludes_contradiction() -> None:
    links = [
        EvidenceLinkInput("supports", 1.0, "primary_source"),   # w 1.0
        EvidenceLinkInput("supports", 0.5, "secondary_source"),  # w 0.5
        EvidenceLinkInput("contradicts", 0.9, "contradiction"),  # w 0.0 -> excluded
    ]
    # (1.0*1.0 + 0.5*0.5) / (1.0 + 0.5) = 1.25/1.5 = 0.8333
    assert _evidence_strength_score(links) == pytest.approx(1.25 / 1.5)


def test_evidence_strength_zero_when_no_weighted_links() -> None:
    assert _evidence_strength_score([]) == 0.0
    assert _evidence_strength_score(
        [EvidenceLinkInput("contradicts", 0.9, "contradiction")]
    ) == 0.0


def test_evidence_strength_weight_table_matches_spec() -> None:
    assert EVIDENCE_STRENGTH_WEIGHTS == {
        "primary_source": 1.0, "corroboration": 0.7, "secondary_source": 0.5,
        "context": 0.3, "inference": 0.2, "contradiction": 0.0,
    }


def test_recency_decays_with_age(scorer: ConfidenceScorer) -> None:
    fresh = scorer.score(
        epistemic_type="claim", accuracy_rate=0.0,
        links=[_link("supports", "corroboration", 0.0)],
        received_at=NOW, object_text=None, now=NOW,
    ).factors.recency_score
    week_old = scorer.score(
        epistemic_type="claim", accuracy_rate=0.0,
        links=[_link("supports", "corroboration", 0.0)],
        received_at=NOW - timedelta(hours=168), object_text=None, now=NOW,
    ).factors.recency_score
    assert fresh == pytest.approx(1.0)
    assert week_old == pytest.approx(0.3679, abs=1e-3)  # exp(-1)


def test_full_composite_with_all_factors(scorer: ConfidenceScorer) -> None:
    # One primary supporting link, count=1.
    links = [_link("supports", "primary_source", 0.8)]
    r = scorer.score(
        epistemic_type="fact", accuracy_rate=0.6, links=links,
        received_at=NOW, object_text="a b c d", now=NOW,
    )
    # factors: trust .6, cross_ref(1)=0.4, evidence=0.8, recency=1.0,
    #          specificity(4 tokens)=1.0, primary=1.0
    expected = (
        0.6 * 0.25 + 0.4 * 0.25 + 0.8 * 0.20 + 1.0 * 0.10 + 1.0 * 0.10 + 1.0 * 0.10
    )
    assert r.confidence_score == pytest.approx(min(expected, 1.0))
    assert r.factors.primary_source_flag is True
    assert r.factors.cross_reference_count == 1
