"""Calendar endpoints (Phase 5 Wave E) — schedule, list, cancel.

POST   /calendar           schedule an approved draft + target for a future time
GET    /calendar           list entries in a [start_date, end_date] range
DELETE /calendar/{id}      soft-cancel a scheduled entry (status only; the row is
                           retained, mirroring Wave A's draft "delete" convention)

Reads require content.read; mutations require content.write. Everything is
workspace-scoped from the auth context.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from oryx.core.db import get_sessionmaker
from oryx.core.dependencies import (
    ActiveWorkspaceContext,
    CurrentPrincipal,
    envelope,
    get_active_workspace,
    get_principal,
    get_request_id,
    require_capability,
)
from oryx.core.models import CalendarEntry
from oryx.services.calendar.schemas import ScheduleDraftRequest
from oryx.services.calendar.service import CalendarService

router = APIRouter(prefix="/calendar", tags=["calendar"])


def _svc() -> CalendarService:
    return CalendarService(get_sessionmaker())


def _entry_dict(e: CalendarEntry) -> dict[str, Any]:
    return {
        "id": str(e.id),
        "workspaceId": str(e.workspace_id),
        "draftId": str(e.draft_id),
        "targetId": str(e.target_id),
        "scheduledAt": e.scheduled_at.isoformat(),
        "status": e.status,
        "publicationId": str(e.publication_id) if e.publication_id else None,
        "createdBy": str(e.created_by),
        "createdAt": e.created_at.isoformat(),
    }


@router.post("", dependencies=[Depends(require_capability("content.write"))])
async def schedule_draft(
    body: ScheduleDraftRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(get_principal),
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    entry = await _svc().schedule_draft(
        draft_id=uuid.UUID(body.draft_id),
        target_id=uuid.UUID(body.target_id),
        scheduled_at=body.scheduled_at,
        account_id=principal.account_id,
        workspace_id=ws.workspace_id,
    )
    return envelope(_entry_dict(entry), request_id=get_request_id(request))


@router.get("", dependencies=[Depends(require_capability("content.read"))])
async def list_calendar(
    request: Request,
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    rows = await _svc().list_calendar(
        workspace_id=ws.workspace_id, start_date=start_date, end_date=end_date
    )
    return envelope(
        [_entry_dict(e) for e in rows], request_id=get_request_id(request)
    )


@router.delete(
    "/{entry_id}", dependencies=[Depends(require_capability("content.write"))]
)
async def cancel_entry(
    entry_id: uuid.UUID,
    request: Request,
    principal: CurrentPrincipal = Depends(get_principal),
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    entry = await _svc().cancel_entry(
        entry_id=entry_id,
        account_id=principal.account_id,
        workspace_id=ws.workspace_id,
    )
    return envelope(_entry_dict(entry), request_id=get_request_id(request))
