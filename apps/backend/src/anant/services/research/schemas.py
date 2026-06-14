"""Request + response models for the research router (Wave E).

Request bodies are snake_case (the intake/admin convention); responses are
camelCase per the shared-types contract.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CreateWorkspaceRequest(BaseModel):
    name: str
    description: str | None = None


class UpdateWorkspaceRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    status: Literal["active", "archived"] | None = None


class AddItemRequest(BaseModel):
    intelligence_object_id: str
    note: str | None = None


class CreatePacketRequest(BaseModel):
    research_workspace_id: str
    name: str
    intelligence_object_ids: list[str] = Field(default_factory=list)


class AcknowledgeConflictRequest(BaseModel):
    intelligence_object_id: str


class ResearchWorkspaceResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    account_id: str = Field(alias="accountId")
    workspace_id: str = Field(alias="workspaceId")
    name: str
    description: str | None = None
    status: Literal["active", "archived"]
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class WorkspaceDetailResponse(ResearchWorkspaceResponse):
    item_count: int = Field(alias="itemCount")


class ResearchWorkspaceItemResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    research_workspace_id: str = Field(alias="researchWorkspaceId")
    intelligence_object_id: str = Field(alias="intelligenceObjectId")
    added_by: str = Field(alias="addedBy")
    note: str | None = None
    added_at: datetime = Field(alias="addedAt")


class ResearchPacketResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    research_workspace_id: str = Field(alias="researchWorkspaceId")
    workspace_id: str = Field(alias="workspaceId")
    name: str
    status: Literal["assembling", "ready", "consumed"]
    intelligence_object_ids: list[str] = Field(alias="intelligenceObjectIds")
    conflict_acknowledged_ids: list[str] = Field(alias="conflictAcknowledgedIds")
    ready_at: datetime | None = Field(default=None, alias="readyAt")
    consumed_at: datetime | None = Field(default=None, alias="consumedAt")
    created_at: datetime = Field(alias="createdAt")


class ReadinessResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    is_ready: bool = Field(alias="isReady")
    blockers: list[str]
