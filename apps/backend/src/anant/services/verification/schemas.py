"""Pydantic response models for the verification router.

Mirrors packages/shared-types/src/verification.ts + scoring.ts. Read-only:
verification runs and credibility records are produced by the pipeline,
never by direct API call.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

VerificationOutcome = Literal["verified", "unverified", "contested", "unverifiable"]
VerificationStatus = Literal["pending", "running", "complete", "failed"]


class ScoringFactorsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source_trust_score: float | None = Field(default=None, alias="sourceTrustScore")
    cross_reference_count_score: float | None = Field(
        default=None, alias="crossReferenceCountScore"
    )
    evidence_strength_score: float | None = Field(
        default=None, alias="evidenceStrengthScore"
    )
    recency_score: float | None = Field(default=None, alias="recencyScore")
    claim_specificity_score: float | None = Field(
        default=None, alias="claimSpecificityScore"
    )
    primary_source_available: float | None = Field(
        default=None, alias="primarySourceAvailable"
    )


class VerificationRunResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    claim_id: str = Field(alias="claimId")
    status: VerificationStatus
    outcome: VerificationOutcome | None = None
    confidence_score: float | None = Field(default=None, alias="confidenceScore")
    cross_reference_count: int | None = Field(default=None, alias="crossReferenceCount")
    primary_source_flag: bool | None = Field(default=None, alias="primarySourceFlag")
    factors: ScoringFactorsResponse
    engine_version: int = Field(alias="engineVersion")
    scoring_version: int = Field(alias="scoringVersion")
    tokens_used: int = Field(alias="tokensUsed")
    started_at: datetime = Field(alias="startedAt")
    completed_at: datetime | None = Field(default=None, alias="completedAt")


class SourceCredibilityResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    workspace_id: str = Field(alias="workspaceId")
    source_id: str = Field(alias="sourceId")
    accuracy_rate: float = Field(alias="accuracyRate")
    verified_claim_count: int = Field(alias="verifiedClaimCount")
    contested_claim_count: int = Field(alias="contestedClaimCount")
    total_claim_count: int = Field(alias="totalClaimCount")
    last_evaluated_at: datetime | None = Field(default=None, alias="lastEvaluatedAt")
    updated_at: datetime = Field(alias="updatedAt")
