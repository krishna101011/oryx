"""Template CRUD endpoints (Phase 5 Wave B).

All routes are workspace-scoped. is_default is never settable by clients.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from oryx.core.db import get_sessionmaker
from oryx.core.dependencies import (
    ActiveWorkspaceContext,
    envelope,
    get_active_workspace,
    get_request_id,
    require_capability,
)
from oryx.services.templates.models import ContentTemplate
from oryx.services.templates.schemas import CreateTemplateRequest, UpdateTemplateRequest
from oryx.services.templates.service import TemplateService

router = APIRouter(prefix="/templates", tags=["content"])


def _svc() -> TemplateService:
    return TemplateService(get_sessionmaker())


def _template_dict(t: ContentTemplate) -> dict[str, Any]:
    return {
        "id": str(t.id),
        "workspaceId": str(t.workspace_id),
        "name": t.name,
        "format": t.format,
        "tone": t.tone,
        "maxWords": t.max_words,
        "minWords": t.min_words,
        "structureHint": t.structure_hint,
        "isDefault": t.is_default,
    }


@router.get(
    "",
    dependencies=[Depends(require_capability("content.read"))],
)
async def list_templates(
    request: Request,
    format: str | None = Query(default=None),
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    svc = _svc()
    async with get_sessionmaker()() as session:
        rows = await svc.list_templates(ws.workspace_id, format=format, session=session)
        await session.commit()
    return envelope([_template_dict(r) for r in rows], request_id=get_request_id(request))


@router.get(
    "/{template_id}",
    dependencies=[Depends(require_capability("content.read"))],
)
async def get_template(
    template_id: uuid.UUID,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    svc = _svc()
    async with get_sessionmaker()() as session:
        t = await svc.get_template(template_id, ws.workspace_id, session=session)
    return envelope(_template_dict(t), request_id=get_request_id(request))


@router.post(
    "",
    dependencies=[Depends(require_capability("content.write"))],
)
async def create_template(
    body: CreateTemplateRequest,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    svc = _svc()
    async with get_sessionmaker()() as session:
        t = await svc.create_template(
            ws.workspace_id,
            name=body.name,
            format=body.format,
            tone=body.tone,
            max_words=body.max_words,
            min_words=body.min_words,
            structure_hint=body.structure_hint,
            session=session,
        )
        await session.commit()
    return envelope(_template_dict(t), request_id=get_request_id(request))


@router.patch(
    "/{template_id}",
    dependencies=[Depends(require_capability("content.write"))],
)
async def update_template(
    template_id: uuid.UUID,
    body: UpdateTemplateRequest,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    from oryx.services.templates.repository import _UNSET
    svc = _svc()
    async with get_sessionmaker()() as session:
        t = await svc.update_template(
            template_id,
            ws.workspace_id,
            name=body.name,
            tone=body.tone,
            max_words=body.max_words if "max_words" in body.model_fields_set else _UNSET,
            min_words=body.min_words if "min_words" in body.model_fields_set else _UNSET,
            structure_hint=body.structure_hint if "structure_hint" in body.model_fields_set else _UNSET,
            is_default_attempted=body.is_default is not None,
            session=session,
        )
        await session.commit()
    return envelope(_template_dict(t), request_id=get_request_id(request))


@router.delete(
    "/{template_id}",
    dependencies=[Depends(require_capability("content.write"))],
)
async def delete_template(
    template_id: uuid.UUID,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    svc = _svc()
    async with get_sessionmaker()() as session:
        await svc.delete_template(template_id, ws.workspace_id, session=session)
        await session.commit()
    return envelope({"deleted": str(template_id)}, request_id=get_request_id(request))
