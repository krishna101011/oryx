"""Workspaces router — /v1/workspaces/current GET + PATCH."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from anant.core.dependencies import (
    ActiveWorkspaceContext,
    db_session,
    envelope,
    get_active_workspace,
    get_request_id,
)
from anant.core.errors import WorkspaceNotFoundError
from anant.core.models import Workspace
from anant.shared.types import ActiveWorkspace
from anant.shared.types import Workspace as WorkspaceSchema

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("/current")
async def get_current(
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict:
    result = await db.execute(select(Workspace).where(Workspace.id == ws.workspace_id))
    workspace = result.scalar_one_or_none()
    if workspace is None:
        raise WorkspaceNotFoundError()
    payload = ActiveWorkspace(
        id=str(workspace.id), name=workspace.name, kind=workspace.kind, role=ws.role
    )
    return envelope(payload.model_dump(by_alias=True), request_id=get_request_id(request))


class _Rename(WorkspaceSchema):
    pass


@router.patch("/current")
async def rename_current(
    body: dict,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict:
    # Phase 2 supports renaming only.
    name = body.get("name")
    if isinstance(name, str) and name.strip():
        await db.execute(
            update(Workspace).where(Workspace.id == ws.workspace_id).values(name=name.strip())
        )
    result = await db.execute(select(Workspace).where(Workspace.id == ws.workspace_id))
    workspace = result.scalar_one_or_none()
    if workspace is None:
        raise WorkspaceNotFoundError()
    payload = ActiveWorkspace(
        id=str(workspace.id), name=workspace.name, kind=workspace.kind, role=ws.role
    )
    return envelope(payload.model_dump(by_alias=True), request_id=get_request_id(request))
