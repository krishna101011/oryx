"""Publishing endpoints (Phase 5 Wave D) — publish a draft + list publications.

POST /drafts/{draft_id}/publish fans a draft out to one or more targets and
returns per-target results (partial success/failure is explicit). GET
/publications lists delivery history. Target CRUD lives in the targets router.
"""
from __future__ import annotations

import uuid
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
from oryx.core.models import Publication
from oryx.services.publishing.engine import PublishingEngine, TargetResult
from oryx.services.publishing.repository import PublicationsRepository
from oryx.services.targets.schemas import PublishRequest

router = APIRouter(tags=["publishing"])


def _publication_dict(p: Publication) -> dict[str, Any]:
    return {
        "id": str(p.id),
        "draftId": str(p.draft_id),
        "versionNumber": p.version_number,
        "targetId": str(p.target_id),
        "workspaceId": str(p.workspace_id),
        "status": p.status,
        "externalId": p.external_id,
        "externalUrl": p.external_url,
        "errorMessage": p.error_message,
        "publishedAt": p.published_at.isoformat() if p.published_at else None,
        "createdAt": p.created_at.isoformat(),
    }


def _result_dict(r: TargetResult) -> dict[str, Any]:
    return {
        "targetId": str(r.target_id),
        "publicationId": str(r.publication_id) if r.publication_id else None,
        "status": r.status,
        "externalId": r.external_id,
        "externalUrl": r.external_url,
        "errorMessage": r.error_message,
    }


@router.post(
    "/drafts/{draft_id}/publish",
    dependencies=[Depends(require_capability("content.write"))],
)
async def publish_draft(
    draft_id: uuid.UUID,
    body: PublishRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(get_principal),
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    engine = PublishingEngine(get_sessionmaker())
    results = await engine.publish_draft(
        draft_id=draft_id,
        target_ids=[uuid.UUID(t) for t in body.target_ids],
        workspace_id=ws.workspace_id,
        account_id=principal.account_id,
    )
    return envelope(
        [_result_dict(r) for r in results], request_id=get_request_id(request)
    )


@router.get(
    "/publications",
    dependencies=[Depends(require_capability("content.read"))],
)
async def list_publications(
    request: Request,
    status: str | None = Query(default=None),
    draft_id: uuid.UUID | None = Query(default=None),
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    async with get_sessionmaker()() as session:
        rows = await PublicationsRepository(session).list_for_workspace(
            workspace_id=ws.workspace_id, status=status, draft_id=draft_id
        )
    return envelope(
        [_publication_dict(p) for p in rows], request_id=get_request_id(request)
    )
