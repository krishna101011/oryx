"""Request + response models for the review router (Wave D).

`note` is typed as a plain `str` (no min_length): empty-note rejection is
enforced in the SERVICE layer (HTTP 400), not the schema — see service.py.
That keeps the not-empty rule in one authoritative place and testable without
going through FastAPI validation.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from oryx.services.claims.schemas import ClaimResponse
from oryx.services.conflicts.schemas import ConflictResponse

AnalystOutcome = Literal[
    "approved",
    "rejected",
    "flagged",
    "override_verified",
    "override_unverified",
    "conflict_resolved_a",
    "conflict_resolved_b",
    "conflict_inconclusive",
]


class ResolveConflictRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    outcome: Literal["a_wins", "b_wins", "inconclusive"]
    note: str


class ReviewClaimRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    outcome: AnalystOutcome
    note: str


class ReviewObjectRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    outcome: Literal["approved", "rejected", "flagged"]
    note: str


class AnalystReviewResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    account_id: str = Field(alias="accountId")
    workspace_id: str = Field(alias="workspaceId")
    entity_type: Literal["claim", "intelligence_object", "conflict"] = Field(
        alias="entityType"
    )
    entity_id: str = Field(alias="entityId")
    outcome: str
    note: str
    created_at: datetime = Field(alias="createdAt")


class ReviewQueueResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    pending_claims: list[ClaimResponse] = Field(alias="pendingClaims")
    open_conflicts: list[ConflictResponse] = Field(alias="openConflicts")
