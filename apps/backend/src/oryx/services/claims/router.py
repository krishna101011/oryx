"""Claims read endpoints (Wave A — no write surface).

Claims are created by the intake.item.received handler only. The
workspace scope comes from the authenticated context (never from a
client-supplied parameter — same tenant-isolation rule as every Phase 3
router), and pagination reuses the Phase 1 cursor envelope (CR-9).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.core.dependencies import (
    ActiveWorkspaceContext,
    db_session,
    envelope,
    get_active_workspace,
    get_request_id,
    require_capability,
)
from oryx.core.errors import NotFoundError, ValidationError
from oryx.core.models import Claim
from oryx.core.pagination import decode_cursor, encode_cursor
from oryx.services.claims.models import EPISTEMIC_TYPES
from oryx.services.claims.schemas import ClaimResponse

router = APIRouter(prefix="/claims", tags=["claims"])

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


def _to_response(row: Claim) -> dict[str, Any]:
    return ClaimResponse(
        id=str(row.id),
        workspace_id=str(row.workspace_id),
        intake_item_id=str(row.intake_item_id),
        text=row.text,
        subject=row.subject,
        predicate=row.predicate,
        object=row.object,
        epistemic_type=row.epistemic_type,
        extractor_version=row.extractor_version,
        classifier_version=row.classifier_version,
        requires_analyst_review=row.requires_analyst_review,
        superseded_by=str(row.superseded_by) if row.superseded_by else None,
        created_at=row.created_at,
    ).model_dump(by_alias=True)


@router.get(
    "",
    dependencies=[Depends(require_capability("verification.read"))],
)
async def list_claims(
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
    intake_item_id: uuid.UUID | None = Query(default=None),
    epistemic_type: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
) -> dict[str, Any]:
    if epistemic_type is not None and epistemic_type not in EPISTEMIC_TYPES:
        raise ValidationError(details={"reason": "invalid_epistemic_type"})

    stmt = (
        select(Claim)
        .where(Claim.workspace_id == ws.workspace_id)
        .order_by(desc(Claim.created_at), desc(Claim.id))
        .limit(limit + 1)
    )
    if intake_item_id is not None:
        stmt = stmt.where(Claim.intake_item_id == intake_item_id)
    if epistemic_type is not None:
        stmt = stmt.where(Claim.epistemic_type == epistemic_type)
    if cursor:
        decoded = decode_cursor(cursor)
        before = datetime.fromisoformat(decoded["created_at"])
        stmt = stmt.where(Claim.created_at < before)

    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    has_more = len(rows) > limit
    rows = rows[:limit]

    next_cursor = None
    if has_more and rows:
        next_cursor = encode_cursor({"created_at": rows[-1].created_at.isoformat()})

    return envelope(
        [_to_response(r) for r in rows],
        request_id=get_request_id(request),
        pagination={"nextCursor": next_cursor, "prevCursor": None},
    )


@router.get(
    "/pending-review",
    dependencies=[Depends(require_capability("verification.read"))],
)
async def pending_review(
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
) -> dict[str, Any]:
    stmt = (
        select(Claim)
        .where(
            Claim.workspace_id == ws.workspace_id,
            Claim.requires_analyst_review.is_(True),
        )
        .order_by(desc(Claim.created_at), desc(Claim.id))
        .limit(limit + 1)
    )
    if cursor:
        decoded = decode_cursor(cursor)
        before = datetime.fromisoformat(decoded["created_at"])
        stmt = stmt.where(Claim.created_at < before)

    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    has_more = len(rows) > limit
    rows = rows[:limit]

    next_cursor = None
    if has_more and rows:
        next_cursor = encode_cursor({"created_at": rows[-1].created_at.isoformat()})

    return envelope(
        [_to_response(r) for r in rows],
        request_id=get_request_id(request),
        pagination={"nextCursor": next_cursor, "prevCursor": None},
    )


@router.get(
    "/{claim_id}",
    dependencies=[Depends(require_capability("verification.read"))],
)
async def get_claim(
    claim_id: uuid.UUID,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict[str, Any]:
    result = await db.execute(
        select(Claim).where(
            Claim.id == claim_id, Claim.workspace_id == ws.workspace_id
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise NotFoundError("Claim not found")
    return envelope(_to_response(row), request_id=get_request_id(request))
