"""Admin verification re-run endpoints (Wave F). Platform-admin only.

Mounted at /v1/admin/verification. Distinct from the workspace-capability
surfaces: these gate on the account-level platform-admin flag (§17.4), the same
gate the Phase 3 manual-ingest admin uses.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request

from oryx.core.db import get_sessionmaker
from oryx.core.dependencies import (
    envelope,
    get_request_id,
    require_platform_admin,
)
from oryx.core.models import Account
from oryx.services.admin.schemas import (
    BudgetResponse,
    ReextractRequest,
    ReextractResponse,
    RescoreRequest,
    RescoreResponse,
    ReverifyRequest,
    ReverifyResponse,
)
from oryx.services.admin.service import AdminVerificationService

router = APIRouter(prefix="/admin/verification", tags=["admin"])


def _svc() -> AdminVerificationService:
    return AdminVerificationService(get_sessionmaker())


@router.post("/reextract")
async def reextract(
    body: ReextractRequest,
    request: Request,
    admin: Account = Depends(require_platform_admin),
) -> dict[str, Any]:
    item_ids = (
        [uuid.UUID(x) for x in body.intake_item_ids]
        if body.intake_item_ids is not None
        else None
    )
    count = await _svc().reextract(
        workspace_id=uuid.UUID(body.workspace_id),
        intake_item_ids=item_ids,
        dry_run=body.dry_run,
        account_id=admin.id,
    )
    payload = ReextractResponse(
        workspace_id=body.workspace_id, queued=count, dry_run=body.dry_run
    ).model_dump(by_alias=True)
    return envelope(payload, request_id=get_request_id(request))


@router.post("/reverify")
async def reverify(
    body: ReverifyRequest,
    request: Request,
    admin: Account = Depends(require_platform_admin),
) -> dict[str, Any]:
    queued = await _svc().reverify(
        workspace_id=uuid.UUID(body.workspace_id),
        claim_ids=[uuid.UUID(x) for x in body.claim_ids],
        reason=body.reason,
        account_id=admin.id,
    )
    return envelope(
        ReverifyResponse(queued=queued).model_dump(by_alias=True),
        request_id=get_request_id(request),
    )


@router.post("/rescore")
async def rescore(
    body: RescoreRequest,
    request: Request,
    admin: Account = Depends(require_platform_admin),
) -> dict[str, Any]:
    updated_runs, updated_objects = await _svc().rescore(
        workspace_id=uuid.UUID(body.workspace_id)
    )
    payload = RescoreResponse(
        updated_runs=updated_runs, updated_objects=updated_objects
    ).model_dump(by_alias=True)
    return envelope(payload, request_id=get_request_id(request))


@router.get("/budget")
async def budget(
    request: Request,
    workspace_id: uuid.UUID,
    admin: Account = Depends(require_platform_admin),
) -> dict[str, Any]:
    data = await _svc().budget(workspace_id=workspace_id)
    payload = BudgetResponse(
        workspace_id=data["workspace_id"],
        tokens_used=data["tokens_used"],
        budget_limit=data["budget_limit"],
        utilization=data["utilization"],
    ).model_dump(by_alias=True)
    return envelope(payload, request_id=get_request_id(request))
