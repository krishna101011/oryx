"""Content draft endpoints (Phase 5 Wave A).

Reads require content.read; mutations require content.write. Everything is
workspace-scoped from the auth context. Generation is a manual analyst action —
the PacketConsumerHandler never generates (it only marks consumed_at).
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
from oryx.core.models import ContentDraft, DraftReview, DraftVersion
from oryx.services.drafts.schemas import (
    ApproveDraftRequest,
    GenerateDraftRequest,
    RegenerateDraftRequest,
    RejectDraftRequest,
    RequestChangesRequest,
    SaveVersionRequest,
    SwitchFormatRequest,
)
from oryx.services.drafts.service import DraftService

router = APIRouter(prefix="/drafts", tags=["content"])


def _svc() -> DraftService:
    return DraftService(get_sessionmaker())


def _draft_dict(d: ContentDraft) -> dict[str, Any]:
    return {
        "id": str(d.id),
        "workspaceId": str(d.workspace_id),
        "accountId": str(d.account_id),
        "packetId": str(d.packet_id),
        "templateId": str(d.template_id) if d.template_id else None,
        "format": d.format,
        "title": d.title,
        "status": d.status,
        "currentVersion": d.current_version,
        "generationModel": d.generation_model,
        "wordCount": d.word_count,
        "publishedAt": d.published_at.isoformat() if d.published_at else None,
        "createdAt": d.created_at.isoformat(),
        "updatedAt": d.updated_at.isoformat(),
    }


def _version_dict(v: DraftVersion) -> dict[str, Any]:
    return {
        "id": str(v.id),
        "draftId": str(v.draft_id),
        "versionNumber": v.version_number,
        "content": v.content,
        "contentHtml": v.content_html,
        "editedBy": str(v.edited_by),
        "editNote": v.edit_note,
        "wordCount": v.word_count,
        "tokenCount": v.token_count,
        "isAiGenerated": v.is_ai_generated,
        "createdAt": v.created_at.isoformat(),
    }


def _review_dict(r: DraftReview) -> dict[str, Any]:
    return {
        "id": str(r.id),
        "draftId": str(r.draft_id),
        "versionNumber": r.version_number,
        "accountId": str(r.account_id),
        "outcome": r.outcome,
        "note": r.note,
        "createdAt": r.created_at.isoformat(),
    }


def _detail_dict(
    draft: ContentDraft,
    current: DraftVersion | None,
    citation_object_ids: list[uuid.UUID],
) -> dict[str, Any]:
    return {
        **_draft_dict(draft),
        "currentContent": current.content if current else None,
        "currentContentHtml": current.content_html if current else None,
        "citationObjectIds": [str(x) for x in citation_object_ids],
    }


async def _detail_response(
    svc: DraftService, workspace_id: uuid.UUID, draft_id: uuid.UUID, request: Request
) -> dict[str, Any]:
    draft, current, citations = await svc.get_draft_detail(
        workspace_id=workspace_id, draft_id=draft_id
    )
    return envelope(
        _detail_dict(draft, current, citations), request_id=get_request_id(request)
    )


# ---------------- generation ----------------


@router.post(
    "/generate",
    dependencies=[Depends(require_capability("content.write"))],
)
async def generate_draft(
    body: GenerateDraftRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(get_principal),
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    svc = _svc()
    draft = await svc.generate_draft(
        packet_id=uuid.UUID(body.packet_id),
        format=body.format,
        instructions=body.instructions,
        account_id=principal.account_id,
        workspace_id=ws.workspace_id,
        template_id=uuid.UUID(body.template_id) if body.template_id else None,
    )
    return await _detail_response(svc, ws.workspace_id, draft.id, request)


@router.post(
    "/{draft_id}/regenerate",
    dependencies=[Depends(require_capability("content.write"))],
)
async def regenerate_draft(
    draft_id: uuid.UUID,
    body: RegenerateDraftRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(get_principal),
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    svc = _svc()
    draft = await svc.regenerate_draft(
        draft_id=draft_id,
        instructions=body.instructions,
        account_id=principal.account_id,
        workspace_id=ws.workspace_id,
    )
    return await _detail_response(svc, ws.workspace_id, draft.id, request)


@router.put(
    "/{draft_id}/version",
    dependencies=[Depends(require_capability("content.write"))],
)
async def save_version(
    draft_id: uuid.UUID,
    body: SaveVersionRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(get_principal),
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    svc = _svc()
    draft = await svc.save_version(
        draft_id=draft_id,
        content=body.content,
        content_html=body.content_html,
        edit_note=body.edit_note,
        account_id=principal.account_id,
        workspace_id=ws.workspace_id,
    )
    return await _detail_response(svc, ws.workspace_id, draft.id, request)


@router.post(
    "/{draft_id}/switch-format",
    dependencies=[Depends(require_capability("content.write"))],
)
async def switch_format(
    draft_id: uuid.UUID,
    body: SwitchFormatRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(get_principal),
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    svc = _svc()
    draft = await svc.switch_format(
        draft_id=draft_id,
        new_format=body.format,
        template_id=uuid.UUID(body.template_id) if body.template_id else None,
        workspace_id=ws.workspace_id,
        account_id=principal.account_id,
    )
    return await _detail_response(svc, ws.workspace_id, draft.id, request)


# ---------------- review workflow (Wave C) ----------------


@router.post(
    "/{draft_id}/submit-review",
    dependencies=[Depends(require_capability("content.write"))],
)
async def submit_review(
    draft_id: uuid.UUID,
    request: Request,
    principal: CurrentPrincipal = Depends(get_principal),
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    svc = _svc()
    draft = await svc.submit_review(
        draft_id=draft_id,
        account_id=principal.account_id,
        workspace_id=ws.workspace_id,
    )
    return await _detail_response(svc, ws.workspace_id, draft.id, request)


@router.post(
    "/{draft_id}/approve",
    dependencies=[Depends(require_capability("content.write"))],
)
async def approve_draft(
    draft_id: uuid.UUID,
    body: ApproveDraftRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(get_principal),
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    svc = _svc()
    draft = await svc.approve_draft(
        draft_id=draft_id,
        account_id=principal.account_id,
        workspace_id=ws.workspace_id,
        note=body.note,
    )
    return await _detail_response(svc, ws.workspace_id, draft.id, request)


@router.post(
    "/{draft_id}/reject",
    dependencies=[Depends(require_capability("content.write"))],
)
async def reject_draft(
    draft_id: uuid.UUID,
    body: RejectDraftRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(get_principal),
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    svc = _svc()
    draft = await svc.reject_draft(
        draft_id=draft_id,
        account_id=principal.account_id,
        workspace_id=ws.workspace_id,
        note=body.note,
    )
    return await _detail_response(svc, ws.workspace_id, draft.id, request)


@router.post(
    "/{draft_id}/request-changes",
    dependencies=[Depends(require_capability("content.write"))],
)
async def request_changes(
    draft_id: uuid.UUID,
    body: RequestChangesRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(get_principal),
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    svc = _svc()
    draft = await svc.request_changes(
        draft_id=draft_id,
        account_id=principal.account_id,
        workspace_id=ws.workspace_id,
        note=body.note,
    )
    return await _detail_response(svc, ws.workspace_id, draft.id, request)


@router.get(
    "/{draft_id}/reviews",
    dependencies=[Depends(require_capability("content.read"))],
)
async def list_reviews(
    draft_id: uuid.UUID,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    rows = await _svc().list_reviews(
        workspace_id=ws.workspace_id, draft_id=draft_id
    )
    return envelope([_review_dict(r) for r in rows], request_id=get_request_id(request))


# ---------------- reads ----------------


@router.get(
    "",
    dependencies=[Depends(require_capability("content.read"))],
)
async def list_drafts(
    request: Request,
    status: str | None = Query(default=None),
    packet_id: uuid.UUID | None = Query(default=None),
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    rows = await _svc().list_drafts(
        workspace_id=ws.workspace_id, status=status, packet_id=packet_id
    )
    return envelope([_draft_dict(r) for r in rows], request_id=get_request_id(request))


@router.get(
    "/{draft_id}",
    dependencies=[Depends(require_capability("content.read"))],
)
async def get_draft(
    draft_id: uuid.UUID,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    return await _detail_response(_svc(), ws.workspace_id, draft_id, request)


@router.get(
    "/{draft_id}/versions",
    dependencies=[Depends(require_capability("content.read"))],
)
async def list_versions(
    draft_id: uuid.UUID,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    rows = await _svc().list_versions(
        workspace_id=ws.workspace_id, draft_id=draft_id
    )
    return envelope([_version_dict(r) for r in rows], request_id=get_request_id(request))
