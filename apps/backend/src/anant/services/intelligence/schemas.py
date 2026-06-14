"""Pydantic response models for the intelligence router.

Mirrors packages/shared-types/src/intelligence.ts. Read-only: objects are
composed by the pipeline, never created by direct API call.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

EpistemicType = Literal[
    "fact", "claim", "rumor", "speculation", "opinion", "unclassified"
]
IntelligenceStatus = Literal[
    "unverified", "verified", "contested", "analyst_approved", "analyst_rejected"
]


class IntelligenceObjectResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    workspace_id: str = Field(alias="workspaceId")
    intake_item_id: str = Field(alias="intakeItemId")
    epistemic_type: EpistemicType = Field(alias="epistemicType")
    confidence_score: float | None = Field(default=None, alias="confidenceScore")
    verification_status: IntelligenceStatus = Field(alias="verificationStatus")
    claim_ids: list[str] = Field(alias="claimIds")
    conflict_ids: list[str] = Field(alias="conflictIds")
    key_facts: dict[str, Any] = Field(alias="keyFacts")
    headline: str
    scoring_version: int = Field(alias="scoringVersion")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class StaleCheckResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    is_stale: bool = Field(alias="isStale")
    current_version: int = Field(alias="currentVersion")
    object_version: int = Field(alias="objectVersion")
