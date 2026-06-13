"""ConfidenceScorer — composite 0.0-1.0 confidence. No AI, pure arithmetic.

Implements §14.4 / ADR-027 exactly:
  - six weighted factors summing to 1.00
  - zero cross-references renormalizes the remaining five (does NOT collapse)
  - epistemic ceiling applied after the composite (ADR-036)
  - evidence_strength is a weighted mean of link.strength by evidence_type
  - unclassified -> None (no score)
"""
from __future__ import annotations

import math
from datetime import datetime

from anant.core.scoring_version import CURRENT_SCORING_VERSION
from anant.services.verification.models import (
    EvidenceLinkInput,
    ScoringFactors,
    ScoringResult,
)

SCORING_VERSION = CURRENT_SCORING_VERSION

# Factor weights — MUST sum to 1.00 (asserted in tests).
W_SOURCE_TRUST = 0.25
W_CROSS_REF = 0.25
W_EVIDENCE_STRENGTH = 0.20
W_RECENCY = 0.10
W_SPECIFICITY = 0.10
W_PRIMARY_SOURCE = 0.10

RECENCY_HALF_LIFE_HOURS = 168.0  # exp(-age_hours / 168)

# Evidence strength weights, by evidence_type. contradiction is excluded
# from the strength mean (weight 0.0).
EVIDENCE_STRENGTH_WEIGHTS: dict[str, float] = {
    "primary_source": 1.0,
    "corroboration": 0.7,
    "secondary_source": 0.5,
    "context": 0.3,
    "inference": 0.2,
    "contradiction": 0.0,
}

# Epistemic ceilings (ADR-036). None -> no score (unclassified).
CEILINGS: dict[str, float | None] = {
    "fact": 1.0,
    "claim": 0.85,
    "speculation": 0.60,
    "rumor": 0.40,
    "opinion": 0.30,
    "unclassified": None,
}


def _cross_reference_score(count: int) -> float:
    if count <= 0:
        return 0.0
    if count == 1:
        return 0.4
    if count == 2:
        return 0.7
    return 1.0


def _specificity_score(object_text: str | None) -> float:
    if object_text is None or not object_text.strip():
        return 0.2
    tokens = object_text.split()
    return 0.5 if len(tokens) <= 3 else 1.0


def _recency_score(received_at: datetime, now: datetime) -> float:
    age_hours = max(0.0, (now - received_at).total_seconds() / 3600.0)
    return math.exp(-age_hours / RECENCY_HALF_LIFE_HOURS)


def _evidence_strength_score(links: list[EvidenceLinkInput]) -> float:
    """Weighted mean of link.strength, weighted by evidence_type weight;
    contradiction (weight 0) is excluded. No weighted links -> 0.0."""
    num = 0.0
    den = 0.0
    for link in links:
        w = EVIDENCE_STRENGTH_WEIGHTS.get(link.evidence_type, 0.0)
        if w <= 0.0:
            continue
        num += link.strength * w
        den += w
    return (num / den) if den > 0.0 else 0.0


class ConfidenceScorer:
    version = SCORING_VERSION

    def score(
        self,
        *,
        epistemic_type: str,
        accuracy_rate: float,
        links: list[EvidenceLinkInput],
        received_at: datetime,
        object_text: str | None,
        now: datetime,
    ) -> ScoringResult:
        cross_reference_count = sum(1 for l in links if l.relationship == "supports")
        primary_source_flag = any(l.evidence_type == "primary_source" for l in links)

        f_source_trust = min(1.0, max(0.0, accuracy_rate))
        f_cross_ref = _cross_reference_score(cross_reference_count)
        f_evidence = _evidence_strength_score(links)
        f_recency = _recency_score(received_at, now)
        f_specificity = _specificity_score(object_text)
        f_primary = 1.0 if primary_source_flag else 0.0

        factors = ScoringFactors(
            source_trust_score=f_source_trust,
            cross_reference_count_score=f_cross_ref,
            evidence_strength_score=f_evidence,
            recency_score=f_recency,
            claim_specificity_score=f_specificity,
            primary_source_available=f_primary,
            cross_reference_count=cross_reference_count,
            primary_source_flag=primary_source_flag,
        )

        ceiling = CEILINGS.get(epistemic_type, None)
        if epistemic_type == "unclassified" or ceiling is None:
            return ScoringResult(confidence_score=None, factors=factors)

        if cross_reference_count == 0:
            # Drop the cross-ref factor and renormalize the remaining five so
            # their weights still sum to 1.00 — absence of corroboration does
            # not collapse the composite (ADR-027).
            remaining = W_SOURCE_TRUST + W_EVIDENCE_STRENGTH + W_RECENCY \
                + W_SPECIFICITY + W_PRIMARY_SOURCE
            composite = (
                f_source_trust * W_SOURCE_TRUST
                + f_evidence * W_EVIDENCE_STRENGTH
                + f_recency * W_RECENCY
                + f_specificity * W_SPECIFICITY
                + f_primary * W_PRIMARY_SOURCE
            ) / remaining
        else:
            composite = (
                f_source_trust * W_SOURCE_TRUST
                + f_cross_ref * W_CROSS_REF
                + f_evidence * W_EVIDENCE_STRENGTH
                + f_recency * W_RECENCY
                + f_specificity * W_SPECIFICITY
                + f_primary * W_PRIMARY_SOURCE
            )

        confidence = min(composite, ceiling)
        return ScoringResult(confidence_score=confidence, factors=factors)
