"""Verification domain entities — frozen dataclasses, no SQLAlchemy."""
from __future__ import annotations

from dataclasses import dataclass

VerificationOutcome = str  # 'verified'|'unverified'|'contested'|'unverifiable'
TERMINAL_OUTCOMES = ("verified", "unverified", "contested", "unverifiable")


@dataclass(frozen=True)
class EvidenceLinkInput:
    """One claim_evidence_link joined with its evidence type, as the engine
    and scorer consume it. The LINK drives the logic (ADR-037); evidence_type
    is carried for the two reads that genuinely need it (primary-source)."""

    relationship: str   # supports | contradicts | contextualizes
    strength: float     # 0.0-1.0
    evidence_type: str  # corroboration | contradiction | ... | primary_source


@dataclass(frozen=True)
class ScoringFactors:
    source_trust_score: float
    cross_reference_count_score: float
    evidence_strength_score: float
    recency_score: float
    claim_specificity_score: float
    primary_source_available: float
    # raw values surfaced onto the verification_runs columns
    cross_reference_count: int
    primary_source_flag: bool

    def as_dict(self) -> dict[str, float]:
        return {
            "source_trust_score": self.source_trust_score,
            "cross_reference_count_score": self.cross_reference_count_score,
            "evidence_strength_score": self.evidence_strength_score,
            "recency_score": self.recency_score,
            "claim_specificity_score": self.claim_specificity_score,
            "primary_source_available": self.primary_source_available,
        }


@dataclass(frozen=True)
class ScoringResult:
    confidence_score: float | None  # None only for unclassified
    factors: ScoringFactors
