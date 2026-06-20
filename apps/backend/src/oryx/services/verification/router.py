"""Verification read endpoints (Wave C — no write surface).

Runs and credibility are produced by the pipeline; the API is read-only.
Workspace scope comes from the authenticated context, never a query param —
the same tenant-isolation rule as the claims and evidence routers.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.core.dependencies import (
    ActiveWorkspaceContext,
    db_session,
    envelope,
    get_active_workspace,
    get_request_id,
    require_capability,
)
from oryx.core.errors import NotFoundError
from oryx.core.models import SourceCredibilityRecord, VerificationRun
from oryx.services.verification.repository import VerificationRepository
from oryx.services.verification.schemas import (
    ScoringFactorsResponse,
    SourceCredibilityResponse,
    VerificationRunResponse,
)

router = APIRouter(prefix="/verification", tags=["verification"])


def _run_dict(row: VerificationRun) -> dict[str, Any]:
    factors = row.factors or {}
    return VerificationRunResponse(
        id=str(row.id),
        claim_id=str(row.claim_id),
        status=row.status,
        outcome=row.outcome,
        confidence_score=row.confidence_score,
        cross_reference_count=row.cross_reference_count,
        primary_source_flag=row.primary_source_flag,
        factors=ScoringFactorsResponse(
            source_trust_score=factors.get("source_trust_score"),
            cross_reference_count_score=factors.get("cross_reference_count_score"),
            evidence_strength_score=factors.get("evidence_strength_score"),
            recency_score=factors.get("recency_score"),
            claim_specificity_score=factors.get("claim_specificity_score"),
            primary_source_available=factors.get("primary_source_available"),
        ),
        engine_version=row.engine_version,
        scoring_version=row.scoring_version,
        tokens_used=row.tokens_used,
        started_at=row.started_at,
        completed_at=row.completed_at,
    ).model_dump(by_alias=True)


def _credibility_dict(row: SourceCredibilityRecord) -> dict[str, Any]:
    return SourceCredibilityResponse(
        workspace_id=str(row.workspace_id),
        source_id=str(row.source_id),
        accuracy_rate=row.accuracy_rate,
        verified_claim_count=row.verified_claim_count,
        contested_claim_count=row.contested_claim_count,
        total_claim_count=row.total_claim_count,
        last_evaluated_at=row.last_evaluated_at,
        updated_at=row.updated_at,
    ).model_dump(by_alias=True)


@router.get(
    "/runs",
    dependencies=[Depends(require_capability("verification.read"))],
)
async def list_runs_for_claim(
    request: Request,
    claim_id: uuid.UUID = Query(...),
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict[str, Any]:
    rows = await VerificationRepository(db).list_runs_for_claim(
        workspace_id=ws.workspace_id, claim_id=claim_id
    )
    return envelope(
        [_run_dict(r) for r in rows], request_id=get_request_id(request)
    )


@router.get(
    "/runs/{run_id}",
    dependencies=[Depends(require_capability("verification.read"))],
)
async def get_run(
    run_id: uuid.UUID,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict[str, Any]:
    row = await VerificationRepository(db).get_run(
        workspace_id=ws.workspace_id, run_id=run_id
    )
    if row is None:
        raise NotFoundError("Verification run not found")
    return envelope(_run_dict(row), request_id=get_request_id(request))


@router.get(
    "/credibility",
    dependencies=[Depends(require_capability("verification.read"))],
)
async def list_credibility(
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict[str, Any]:
    rows = await VerificationRepository(db).list_credibility(ws.workspace_id)
    return envelope(
        [_credibility_dict(r) for r in rows], request_id=get_request_id(request)
    )


@router.get(
    "/credibility/{source_id}",
    dependencies=[Depends(require_capability("verification.read"))],
)
async def get_credibility(
    source_id: uuid.UUID,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict[str, Any]:
    row = await VerificationRepository(db).get_credibility(
        workspace_id=ws.workspace_id, source_id=source_id
    )
    if row is None:
        raise NotFoundError("Source credibility record not found")
    return envelope(_credibility_dict(row), request_id=get_request_id(request))
