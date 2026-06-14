"""Research workspace + packet endpoints (Wave E).

Reads require research.read; mutations require research.write. Everything is
workspace-scoped from the auth context. The packet readiness gate returns
HTTP 409 (PreconditionFailedError) with the blocker list when not ready.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from anant.core.db import get_sessionmaker
from anant.core.dependencies import (
    ActiveWorkspaceContext,
    CurrentPrincipal,
    envelope,
    get_active_workspace,
    get_principal,
    get_request_id,
    require_capability,
)
from anant.core.models import (
    IntelligenceObject,
    ResearchPacket,
    ResearchWorkspace,
    ResearchWorkspaceItem,
)
from anant.services.research.schemas import (
    AcknowledgeConflictRequest,
    AddItemRequest,
    CreatePacketRequest,
    CreateWorkspaceRequest,
    UpdateWorkspaceRequest,
)
from anant.services.research.service import ResearchService

router = APIRouter(prefix="/research", tags=["research"])


def _svc() -> ResearchService:
    return ResearchService(get_sessionmaker())


def _ws_dict(row: ResearchWorkspace) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "accountId": str(row.account_id),
        "workspaceId": str(row.workspace_id),
        "name": row.name,
        "description": row.description,
        "status": row.status,
        "createdAt": row.created_at.isoformat(),
        "updatedAt": row.updated_at.isoformat(),
    }


def _packet_dict(row: ResearchPacket) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "researchWorkspaceId": str(row.research_workspace_id),
        "workspaceId": str(row.workspace_id),
        "name": row.name,
        "status": row.status,
        "intelligenceObjectIds": [str(x) for x in (row.intelligence_object_ids or [])],
        "conflictAcknowledgedIds": [
            str(x) for x in (row.conflict_acknowledged_ids or [])
        ],
        "readyAt": row.ready_at.isoformat() if row.ready_at else None,
        "consumedAt": row.consumed_at.isoformat() if row.consumed_at else None,
        "createdAt": row.created_at.isoformat(),
    }


def _object_summary(obj: IntelligenceObject | None) -> dict[str, Any] | None:
    if obj is None:
        return None
    return {
        "id": str(obj.id),
        "headline": obj.headline,
        "epistemicType": obj.epistemic_type,
        "confidenceScore": obj.confidence_score,
        "verificationStatus": obj.verification_status,
    }


def _item_dict(
    item: ResearchWorkspaceItem, obj: IntelligenceObject | None
) -> dict[str, Any]:
    return {
        "researchWorkspaceId": str(item.research_workspace_id),
        "intelligenceObjectId": str(item.intelligence_object_id),
        "addedBy": str(item.added_by),
        "note": item.note,
        "addedAt": item.added_at.isoformat(),
        "object": _object_summary(obj),
    }


# ---------------- workspaces ----------------


@router.post(
    "/workspaces",
    dependencies=[Depends(require_capability("research.write"))],
)
async def create_workspace(
    body: CreateWorkspaceRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(get_principal),
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    row = await _svc().create_workspace(
        workspace_id=ws.workspace_id,
        account_id=principal.account_id,
        name=body.name,
        description=body.description,
    )
    return envelope(_ws_dict(row), request_id=get_request_id(request))


@router.get(
    "/workspaces",
    dependencies=[Depends(require_capability("research.read"))],
)
async def list_workspaces(
    request: Request,
    principal: CurrentPrincipal = Depends(get_principal),
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    rows = await _svc().list_workspaces(
        workspace_id=ws.workspace_id, account_id=principal.account_id
    )
    return envelope([_ws_dict(r) for r in rows], request_id=get_request_id(request))


@router.get(
    "/workspaces/{rws_id}",
    dependencies=[Depends(require_capability("research.read"))],
)
async def get_workspace(
    rws_id: uuid.UUID,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    row, count = await _svc().get_workspace_detail(
        workspace_id=ws.workspace_id, rws_id=rws_id
    )
    payload = {**_ws_dict(row), "itemCount": count}
    return envelope(payload, request_id=get_request_id(request))


@router.patch(
    "/workspaces/{rws_id}",
    dependencies=[Depends(require_capability("research.write"))],
)
async def update_workspace(
    rws_id: uuid.UUID,
    body: UpdateWorkspaceRequest,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    row = await _svc().update_workspace(
        workspace_id=ws.workspace_id,
        rws_id=rws_id,
        name=body.name,
        description=body.description,
        status=body.status,
    )
    return envelope(_ws_dict(row), request_id=get_request_id(request))


# ---------------- items ----------------


@router.post(
    "/workspaces/{rws_id}/items",
    dependencies=[Depends(require_capability("research.write"))],
)
async def add_item(
    rws_id: uuid.UUID,
    body: AddItemRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(get_principal),
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    result = await _svc().add_item(
        workspace_id=ws.workspace_id,
        rws_id=rws_id,
        account_id=principal.account_id,
        object_id=uuid.UUID(body.intelligence_object_id),
        note=body.note,
    )
    return envelope(result, request_id=get_request_id(request))


@router.delete(
    "/workspaces/{rws_id}/items/{object_id}",
    dependencies=[Depends(require_capability("research.write"))],
)
async def remove_item(
    rws_id: uuid.UUID,
    object_id: uuid.UUID,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    result = await _svc().remove_item(
        workspace_id=ws.workspace_id, rws_id=rws_id, object_id=object_id
    )
    return envelope(result, request_id=get_request_id(request))


@router.get(
    "/workspaces/{rws_id}/items",
    dependencies=[Depends(require_capability("research.read"))],
)
async def list_items(
    rws_id: uuid.UUID,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    pairs = await _svc().list_items(workspace_id=ws.workspace_id, rws_id=rws_id)
    return envelope(
        [_item_dict(item, obj) for item, obj in pairs],
        request_id=get_request_id(request),
    )


# ---------------- packets ----------------


@router.post(
    "/packets",
    dependencies=[Depends(require_capability("research.write"))],
)
async def create_packet(
    body: CreatePacketRequest,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    packet = await _svc().create_packet(
        workspace_id=ws.workspace_id,
        rws_id=uuid.UUID(body.research_workspace_id),
        name=body.name,
        object_ids=[uuid.UUID(x) for x in body.intelligence_object_ids],
    )
    return envelope(_packet_dict(packet), request_id=get_request_id(request))


@router.get(
    "/packets",
    dependencies=[Depends(require_capability("research.read"))],
)
async def list_packets(
    request: Request,
    status: str | None = Query(default=None),
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    rows = await _svc().list_packets(workspace_id=ws.workspace_id, status=status)
    return envelope([_packet_dict(r) for r in rows], request_id=get_request_id(request))


@router.get(
    "/packets/{packet_id}",
    dependencies=[Depends(require_capability("research.read"))],
)
async def get_packet(
    packet_id: uuid.UUID,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    packet = await _svc().get_packet(workspace_id=ws.workspace_id, packet_id=packet_id)
    return envelope(_packet_dict(packet), request_id=get_request_id(request))


@router.get(
    "/packets/{packet_id}/readiness",
    dependencies=[Depends(require_capability("research.read"))],
)
async def packet_readiness(
    packet_id: uuid.UUID,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    readiness = await _svc().check_readiness(
        workspace_id=ws.workspace_id, packet_id=packet_id
    )
    return envelope(
        {"isReady": readiness.is_ready, "blockers": readiness.blockers},
        request_id=get_request_id(request),
    )


@router.post(
    "/packets/{packet_id}/ready",
    dependencies=[Depends(require_capability("research.write"))],
)
async def mark_packet_ready(
    packet_id: uuid.UUID,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    packet = await _svc().mark_ready(
        workspace_id=ws.workspace_id, packet_id=packet_id
    )
    return envelope(_packet_dict(packet), request_id=get_request_id(request))


@router.post(
    "/packets/{packet_id}/acknowledge-conflict",
    dependencies=[Depends(require_capability("research.write"))],
)
async def acknowledge_conflict(
    packet_id: uuid.UUID,
    body: AcknowledgeConflictRequest,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    result = await _svc().acknowledge_conflict(
        workspace_id=ws.workspace_id,
        packet_id=packet_id,
        object_id=uuid.UUID(body.intelligence_object_id),
    )
    return envelope(result, request_id=get_request_id(request))
