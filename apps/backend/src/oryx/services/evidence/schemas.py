"""Pydantic response models for the evidence router.

Mirrors packages/shared-types/src/evidence.ts. Read-only surface —
evidence is created by the event handler, never by direct API call.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EvidenceType = Literal[
    "corroboration", "contradiction", "context",
    "primary_source", "secondary_source", "inference",
]
EvidenceRelationship = Literal["supports", "contradicts", "contextualizes"]


class ClaimEvidenceLinkResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    claim_id: str = Field(alias="claimId")
    evidence_id: str = Field(alias="evidenceId")
    relationship: EvidenceRelationship
    strength: float
    linker_version: int = Field(alias="linkerVersion")


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    workspace_id: str = Field(alias="workspaceId")
    intake_item_id: str = Field(alias="intakeItemId")
    evidence_type: EvidenceType = Field(alias="evidenceType")
    text: str
    source_deleted: bool = Field(alias="sourceDeleted")
    created_at: datetime = Field(alias="createdAt")


class EvidenceWithLinkResponse(EvidenceResponse):
    link: ClaimEvidenceLinkResponse
