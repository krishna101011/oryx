"""Pydantic response models for the conflicts router.

Mirrors packages/shared-types/src/conflicts.ts (camelCase on the wire).
Conflict records are produced by the pipeline; resolution flows through the
review router. The GET surface here is read-only.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from oryx.services.claims.schemas import ClaimResponse

ConflictType = Literal[
    "direct_contradiction",
    "factual_disagreement",
    "temporal_inconsistency",
    "scope_difference",
]
ConflictStatus = Literal[
    "open",
    "resolved_a_wins",
    "resolved_b_wins",
    "resolved_inconclusive",
    "resolved_system",
    "analyst_reviewed",
]


class ConflictResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    workspace_id: str = Field(alias="workspaceId")
    claim_a_id: str = Field(alias="claimAId")
    claim_b_id: str = Field(alias="claimBId")
    conflict_type: ConflictType = Field(alias="conflictType")
    severity: float
    status: ConflictStatus
    resolution_note: str | None = Field(default=None, alias="resolutionNote")
    resolved_by_kind: Literal["system", "analyst"] | None = Field(
        default=None, alias="resolvedByKind"
    )
    resolved_at: datetime | None = Field(default=None, alias="resolvedAt")
    created_at: datetime = Field(alias="createdAt")


class ConflictDetailResponse(ConflictResponse):
    claim_a: ClaimResponse = Field(alias="claimA")
    claim_b: ClaimResponse = Field(alias="claimB")
    claim_a_score: float | None = Field(default=None, alias="claimAScore")
    claim_b_score: float | None = Field(default=None, alias="claimBScore")
    claim_a_evidence_counts: dict[str, int] = Field(alias="claimAEvidenceCounts")
    claim_b_evidence_counts: dict[str, int] = Field(alias="claimBEvidenceCounts")
