"""Publish-target endpoints (Phase 5 Wave D).

Reads require content.read; mutations require content.write. Everything is
workspace-scoped from the auth context. Credentials are NEVER serialized — the
target dict has no credentials field at all (§13.2).
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request

from oryx.core.db import get_sessionmaker
from oryx.core.dependencies import (
    ActiveWorkspaceContext,
    envelope,
    get_active_workspace,
    get_request_id,
    require_capability,
)
from oryx.core.models import PublishTarget
from oryx.services.targets.schemas import CreateTargetRequest
from oryx.services.targets.service import TargetService

router = APIRouter(prefix="/targets", tags=["publishing"])


def _svc() -> TargetService:
    return TargetService(get_sessionmaker())


def _target_dict(t: PublishTarget) -> dict[str, Any]:
    # NOTE: credentials / credentials_iv are deliberately ABSENT (§13.2).
    return {
        "id": str(t.id),
        "workspaceId": str(t.workspace_id),
        "name": t.name,
        "channel": t.channel,
        "config": dict(t.config or {}),
        "isActive": t.is_active,
        "lastHealthAt": t.last_health_at.isoformat() if t.last_health_at else None,
        "lastHealthOk": t.last_health_ok,
        "createdAt": t.created_at.isoformat(),
    }


@router.post("", dependencies=[Depends(require_capability("content.write"))])
async def create_target(
    body: CreateTargetRequest,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    target = await _svc().create_target(
        workspace_id=ws.workspace_id,
        name=body.name,
        channel=body.channel,
        credentials=body.credentials,
        config=body.config,
    )
    return envelope(_target_dict(target), request_id=get_request_id(request))


@router.get("", dependencies=[Depends(require_capability("content.read"))])
async def list_targets(
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    rows = await _svc().list_targets(workspace_id=ws.workspace_id)
    return envelope(
        [_target_dict(t) for t in rows], request_id=get_request_id(request)
    )


@router.get("/{target_id}", dependencies=[Depends(require_capability("content.read"))])
async def get_target(
    target_id: uuid.UUID,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    target = await _svc().get_target(
        workspace_id=ws.workspace_id, target_id=target_id
    )
    return envelope(_target_dict(target), request_id=get_request_id(request))


@router.delete(
    "/{target_id}", dependencies=[Depends(require_capability("content.write"))]
)
async def delete_target(
    target_id: uuid.UUID,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    await _svc().delete_target(workspace_id=ws.workspace_id, target_id=target_id)
    return envelope({"deleted": True}, request_id=get_request_id(request))


@router.post(
    "/{target_id}/health-check",
    dependencies=[Depends(require_capability("content.write"))],
)
async def health_check(
    target_id: uuid.UUID,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    ok = await _svc().health_check(
        workspace_id=ws.workspace_id, target_id=target_id
    )
    return envelope({"ok": ok}, request_id=get_request_id(request))
