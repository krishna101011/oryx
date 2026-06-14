"""Intelligence object read endpoints (Wave E). Read-only + workspace-scoped."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from anant.core.dependencies import (
    ActiveWorkspaceContext,
    db_session,
    envelope,
    get_active_workspace,
    get_request_id,
    require_capability,
)
from anant.core.errors import NotFoundError
from anant.core.models import IntelligenceObject
from anant.core.scoring_version import CURRENT_SCORING_VERSION
from anant.services.intelligence.repository import IntelligenceRepository
from anant.services.intelligence.schemas import (
    IntelligenceObjectResponse,
    StaleCheckResponse,
)

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


def _object_dict(row: IntelligenceObject) -> dict[str, Any]:
    return IntelligenceObjectResponse(
        id=str(row.id),
        workspace_id=str(row.workspace_id),
        intake_item_id=str(row.intake_item_id),
        epistemic_type=row.epistemic_type,
        confidence_score=row.confidence_score,
        verification_status=row.verification_status,
        claim_ids=[str(c) for c in (row.claim_ids or [])],
        conflict_ids=[str(c) for c in (row.conflict_ids or [])],
        key_facts=row.key_facts or {},
        headline=row.headline,
        scoring_version=row.scoring_version,
        created_at=row.created_at,
        updated_at=row.updated_at,
    ).model_dump(by_alias=True)


@router.get(
    "/objects",
    dependencies=[Depends(require_capability("verification.read"))],
)
async def list_objects(
    request: Request,
    status: str | None = Query(default=None),
    min_score: float | None = Query(default=None),
    epistemic_type: str | None = Query(default=None),
    search: str | None = Query(default=None),
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict[str, Any]:
    rows = await IntelligenceRepository(db).list_objects(
        workspace_id=ws.workspace_id,
        status=status,
        min_score=min_score,
        epistemic_type=epistemic_type,
        search=search,
    )
    return envelope(
        [_object_dict(r) for r in rows], request_id=get_request_id(request)
    )


@router.get(
    "/objects/{object_id}",
    dependencies=[Depends(require_capability("verification.read"))],
)
async def get_object(
    object_id: uuid.UUID,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict[str, Any]:
    row = await IntelligenceRepository(db).get_object(
        workspace_id=ws.workspace_id, object_id=object_id
    )
    if row is None:
        raise NotFoundError("Intelligence object not found")
    return envelope(_object_dict(row), request_id=get_request_id(request))


@router.get(
    "/objects/{object_id}/stale",
    dependencies=[Depends(require_capability("verification.read"))],
)
async def object_stale(
    object_id: uuid.UUID,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict[str, Any]:
    row = await IntelligenceRepository(db).get_object(
        workspace_id=ws.workspace_id, object_id=object_id
    )
    if row is None:
        raise NotFoundError("Intelligence object not found")
    payload = StaleCheckResponse(
        is_stale=row.scoring_version < CURRENT_SCORING_VERSION,
        current_version=CURRENT_SCORING_VERSION,
        object_version=row.scoring_version,
    ).model_dump(by_alias=True)
    return envelope(payload, request_id=get_request_id(request))
