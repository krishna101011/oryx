"""Analyst review endpoints (Wave D).

POST routes record analyst decisions (analyst_reviews + verification_audit_log)
and require verification.write; the queue GET is read-only. The conflict
resolve POST lives under /conflicts (conflicts.router) but shares this
service.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request

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
from anant.core.models import Claim, ConflictRecord
from anant.services.review.schemas import (
    ReviewClaimRequest,
    ReviewObjectRequest,
    ReviewQueueResponse,
)
from anant.services.review.service import ReviewService

router = APIRouter(prefix="/review", tags=["review"])


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


def _conflict_response(row: ConflictRecord) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "workspaceId": str(row.workspace_id),
        "claimAId": str(row.claim_a_id),
        "claimBId": str(row.claim_b_id),
        "conflictType": row.conflict_type,
        "severity": row.severity,
        "status": row.status,
        "resolutionNote": row.resolution_note,
        "resolvedByKind": row.resolved_by_kind,
        "resolvedAt": row.resolved_at,
        "createdAt": row.created_at,
    }


@router.post(
    "/claims/{claim_id}",
    dependencies=[Depends(require_capability("verification.write"))],
)
async def review_claim(
    claim_id: uuid.UUID,
    body: ReviewClaimRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(get_principal),
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    result = await ReviewService(get_sessionmaker()).review_claim(
        claim_id=claim_id,
        workspace_id=ws.workspace_id,
        account_id=principal.account_id,
        outcome=body.outcome,
        note=body.note,
    )
    return envelope(result, request_id=get_request_id(request))


@router.post(
    "/objects/{object_id}",
    dependencies=[Depends(require_capability("verification.write"))],
)
async def review_object(
    object_id: uuid.UUID,
    body: ReviewObjectRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(get_principal),
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    result = await ReviewService(get_sessionmaker()).review_object(
        object_id=object_id,
        workspace_id=ws.workspace_id,
        account_id=principal.account_id,
        outcome=body.outcome,
        note=body.note,
    )
    return envelope(result, request_id=get_request_id(request))


@router.get(
    "/queue",
    dependencies=[Depends(require_capability("verification.read"))],
)
async def review_queue(
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
) -> dict[str, Any]:
    queue = await ReviewService(get_sessionmaker()).get_queue(ws.workspace_id)
    payload = ReviewQueueResponse(
        pending_claims=[_claim_response(c) for c in queue["pendingClaims"]],
        open_conflicts=[_conflict_response(c) for c in queue["openConflicts"]],
    ).model_dump(by_alias=True)
    return envelope(payload, request_id=get_request_id(request))
