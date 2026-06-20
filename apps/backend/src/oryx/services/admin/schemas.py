"""Request/response models for the admin verification re-run surface (Wave F).

Platform-admin only. These are operational tools: re-extract claims, re-verify,
and re-score after an engine/scorer version change. Request bodies are
snake_case (the admin/intake convention).
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ReextractRequest(BaseModel):
    workspace_id: str
    intake_item_ids: list[str] | None = None  # null = all items in workspace
    dry_run: bool = False


class ReextractResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    workspace_id: str = Field(alias="workspaceId")
    queued: int
    dry_run: bool = Field(alias="dryRun")


class ReverifyRequest(BaseModel):
    workspace_id: str
    claim_ids: list[str]
    reason: str


class ReverifyResponse(BaseModel):
    queued: int


class RescoreRequest(BaseModel):
    workspace_id: str
    scoring_version: int


class RescoreResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    updated_runs: int = Field(alias="updatedRuns")
    updated_objects: int = Field(alias="updatedObjects")


class BudgetResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    workspace_id: str = Field(alias="workspaceId")
    tokens_used: int = Field(alias="tokensUsed")
    budget_limit: int = Field(alias="budgetLimit")
    utilization: float
