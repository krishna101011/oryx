"""Evidence read endpoints (Wave B — no write surface).

Workspace scope comes from the authenticated context, never from a
client-supplied parameter; same tenant-isolation rule as the claims
router.
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
from oryx.core.models import ClaimEvidenceLink, Evidence
from oryx.services.evidence.repository import EvidenceRepository
from oryx.services.evidence.schemas import (
    ClaimEvidenceLinkResponse,
    EvidenceResponse,
    EvidenceWithLinkResponse,
)

router = APIRouter(prefix="/evidence", tags=["evidence"])


def _evidence_dict(row: Evidence) -> dict[str, Any]:
    return EvidenceResponse(
        id=str(row.id),
        workspace_id=str(row.workspace_id),
        intake_item_id=str(row.intake_item_id),
        evidence_type=row.evidence_type,
        text=row.text,
        source_deleted=row.source_deleted,
        created_at=row.created_at,
    ).model_dump(by_alias=True)


def _with_link_dict(row: Evidence, link: ClaimEvidenceLink) -> dict[str, Any]:
    payload = EvidenceWithLinkResponse(
        id=str(row.id),
        workspace_id=str(row.workspace_id),
        intake_item_id=str(row.intake_item_id),
        evidence_type=row.evidence_type,
        text=row.text,
        source_deleted=row.source_deleted,
        created_at=row.created_at,
        link=ClaimEvidenceLinkResponse(
            claim_id=str(link.claim_id),
            evidence_id=str(link.evidence_id),
            relationship=link.relationship,
            strength=link.strength,
            linker_version=link.linker_version,
        ),
    )
    return payload.model_dump(by_alias=True)


@router.get(
    "",
    dependencies=[Depends(require_capability("verification.read"))],
)
async def list_evidence_for_claim(
    request: Request,
    claim_id: uuid.UUID = Query(...),
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict[str, Any]:
    repo = EvidenceRepository(db)
    # Claim must belong to the caller's workspace before any links leak.
    claim = await repo.get_claim(workspace_id=ws.workspace_id, claim_id=claim_id)
    if claim is None:
        raise NotFoundError("Claim not found")
    pairs = await repo.list_evidence_with_links(
        workspace_id=ws.workspace_id, claim_id=claim_id
    )
    return envelope(
        [_with_link_dict(ev, link) for ev, link in pairs],
        request_id=get_request_id(request),
    )


@router.get(
    "/{evidence_id}",
    dependencies=[Depends(require_capability("verification.read"))],
)
async def get_evidence(
    evidence_id: uuid.UUID,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict[str, Any]:
    row = await EvidenceRepository(db).get_evidence(
        workspace_id=ws.workspace_id, evidence_id=evidence_id
    )
    if row is None:
        raise NotFoundError("Evidence not found")
    return envelope(_evidence_dict(row), request_id=get_request_id(request))
