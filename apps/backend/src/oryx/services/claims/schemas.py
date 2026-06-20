"""Pydantic response models for the claims router.

Mirrors packages/shared-types/src/claims.ts (camelCase on the wire).
Read-only in Wave A: claims are created by the event handler, never
by direct API call, so there are no request bodies here.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EpistemicType = Literal[
    "fact", "claim", "rumor", "speculation", "opinion", "unclassified"
]


class ClaimResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    workspace_id: str = Field(alias="workspaceId")
    intake_item_id: str = Field(alias="intakeItemId")
    text: str
    subject: str
    predicate: str
    object: str | None = None
    epistemic_type: EpistemicType = Field(alias="epistemicType")
    extractor_version: int = Field(alias="extractorVersion")
    classifier_version: int | None = Field(default=None, alias="classifierVersion")
    requires_analyst_review: bool = Field(alias="requiresAnalystReview")
    superseded_by: str | None = Field(default=None, alias="supersededBy")
    created_at: datetime = Field(alias="createdAt")
