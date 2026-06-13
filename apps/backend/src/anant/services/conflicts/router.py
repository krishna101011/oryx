"""Conflict read + resolve endpoints (Wave D).

GETs are read-only and workspace-scoped from the auth context. The resolve
POST routes under /conflicts but its transactional logic (analyst override +
audit + supersession) lives in the review service, alongside the other
analyst actions.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from anant.core.db import get_sessionmaker
from anant.core.dependencies import (
    ActiveWorkspaceContext,
    CurrentPrincipal,
    db_session,
    envelope,
    get_active_workspace,
    get_principal,
    get_request_id,
    require_capability,
)
from anant.core.errors import NotFoundError
from anant.core.models import Claim, ConflictRecord
from anant.services.conflicts.repository import ConflictRepository
from anant.services.conflicts.schemas import (
    ConflictDetailResponse,
    ConflictResponse,
)
from anant.services.review.schemas import ResolveConflictRequest
from anant.services.review.service import ReviewService

router = APIRouter(prefix="/conflicts", tags=["conflicts"])


def _claim_response(claim: Claim) -> dict[str, Any]:
    return {
        "id": str(claim.id),
        "workspaceId": str(claim.workspace_id),
        "intakeItemId": str(claim.intake_item_id),
        "text": claim.text,
        "subject": claim.subject,
        "predicate": claim.predicate,
        "object": claim.object,
        "epistemicType": claim.epistemic_type,
        "extractorVersion": claim.extractor_version,
        "classifierVersion": claim.classifier_version,
        "requiresAnalystReview": claim.requires_analyst_review,
        "supersededBy": str(claim.superseded_by) if claim.superseded_by else None,
        "createdAt": claim.created_at,
    }


def _conflict_dict(row: ConflictRecord) -> dict[str, Any]:
    return ConflictResponse(
        id=str(row.id),
        workspace_id=str(row.workspace_id),
        claim_a_id=str(row.claim_a_id),
        claim_b_id=str(row.claim_b_id),
        conflict_type=row.conflict_type,
        severity=row.severity,
        status=row.status,
        resolution_note=row.resolution_note,
        resolved_by_kind=row.resolved_by_kind,
        resolved_at=row.resolved_at,
        created_at=row.created_at,
    ).model_dump(by_alias=True)


@router.get(
    "",
    dependencies=[Depends(require_capability("verification.read"))],
)
async def list_conflicts(
    request: Request,
    status: str | None = Query(default=None),
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict[str, Any]:
    rows = await ConflictRepository(db).list_conflicts(
        workspace_id=ws.workspace_id, status=status
    )
    return envelope(
        [_conflict_dict(r) for r in rows], request_id=get_request_id(request)
    )


@router.get(
    "/{conflict_id}",
    dependencies=[Depends(require_capability("verification.read"))],
)
async def get_conflict(
    conflict_id: uuid.UUID,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict[str, Any]:
    repo = ConflictRepository(db)
    row = await repo.get_conflict(workspace_id=ws.workspace_id, conflict_id=conflict_id)
    if row is None:
        raise NotFoundError("Conflict not found")
    claim_a = await repo.get_claim(workspace_id=ws.workspace_id, claim_id=row.claim_a_id)
    claim_b = await repo.get_claim(workspace_id=ws.workspace_id, claim_id=row.claim_b_id)
    if claim_a is None or claim_b is None:
        raise NotFoundError("Conflict claims not found")

    detail = ConflictDetailResponse(
        id=str(row.id),
        workspace_id=str(row.workspace_id),
        claim_a_id=str(row.claim_a_id),
        claim_b_id=str(row.claim_b_id),
        conflict_type=row.conflict_type,
        severity=row.severity,
        status=row.status,
        resolution_note=row.resolution_note,
        resolved_by_kind=row.resolved_by_kind,
        resolved_at=row.resolved_at,
        created_at=row.created_at,
        claim_a=_claim_response(claim_a),
        claim_b=_claim_response(claim_b),
        claim_a_score=await repo.latest_confidence(row.claim_a_id),
        claim_b_score=await repo.latest_confidence(row.claim_b_id),
        claim_a_evidence_counts=await repo.evidence_type_counts(row.claim_a_id),
        claim_b_evidence_counts=await repo.evidence_type_counts(row.claim_b_id),
    ).model_dump(by_alias=True)
    return envelope(detail, request_id=get_request_id(request))


@router.post(
    "/{conflict_id}/resolve",
    dependencies=[Depends(require_capability("verification.write"))],
)
async def resolve_conflict(
    conflict_id: uuid.UUID,
    body: ResolveConflictRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(get_principal),
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    result = await ReviewService(get_sessionmaker()).resolve_conflict(
        conflict_id=conflict_id,
        workspace_id=ws.workspace_id,
        account_id=principal.account_id,
        outcome=body.outcome,
        note=body.note,
    )
    return envelope(result, request_id=get_request_id(request))
