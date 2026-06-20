"""Sources router.

- /v1/sources/catalog          — read the curated catalog
- /v1/sources/workspace        — read enabled sources for the current workspace
- /v1/sources/workspace/{key}  — toggle / confidence override
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.core.dependencies import (
    ActiveWorkspaceContext,
    db_session,
    envelope,
    get_active_workspace,
    get_request_id,
)
from oryx.core.errors import NotFoundError
from oryx.core.models import SourceCatalog, WorkspaceSource
from oryx.shared.types import (
    SourceCatalogEntry,
    UpdateWorkspaceSourceRequest,
)
from oryx.shared.types import (
    WorkspaceSource as WorkspaceSourceSchema,
)

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("/catalog")
async def get_catalog(
    request: Request, db: AsyncSession = Depends(db_session)
) -> dict:
    result = await db.execute(select(SourceCatalog).order_by(SourceCatalog.name))
    rows = result.scalars().all()
    payload = [
        SourceCatalogEntry(
            key=r.key,
            name=r.name,
            url=r.url,
            focus=r.focus,
            editorialConfidence=r.editorial_confidence,
        ).model_dump(by_alias=True)
        for r in rows
    ]
    return envelope(payload, request_id=get_request_id(request))


@router.get("/workspace")
async def get_workspace_sources(
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict:
    result = await db.execute(
        select(WorkspaceSource).where(WorkspaceSource.workspace_id == ws.workspace_id)
    )
    rows = result.scalars().all()
    payload = [
        WorkspaceSourceSchema(
            workspaceId=str(r.workspace_id),
            sourceKey=r.source_key,
            enabled=r.enabled,
            confidenceOverride=r.confidence_override,
            addedAt=r.added_at,
        ).model_dump(by_alias=True)
        for r in rows
    ]
    return envelope(payload, request_id=get_request_id(request))


@router.put("/workspace/{source_key}")
async def upsert_workspace_source(
    source_key: str,
    body: UpdateWorkspaceSourceRequest,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict:
    catalog = await db.execute(
        select(SourceCatalog).where(SourceCatalog.key == source_key)
    )
    if catalog.scalar_one_or_none() is None:
        raise NotFoundError("Source not in catalog")

    values: dict = {"workspace_id": ws.workspace_id, "source_key": source_key}
    if body.enabled is not None:
        values["enabled"] = body.enabled
    if body.confidence_override is not None:
        values["confidence_override"] = body.confidence_override

    # Upsert: insert with on-conflict-do-update.
    stmt = pg_insert(WorkspaceSource).values(**values)
    update_cols = {k: stmt.excluded[k] for k in values if k not in ("workspace_id", "source_key")}
    if update_cols:
        stmt = stmt.on_conflict_do_update(
            index_elements=["workspace_id", "source_key"], set_=update_cols
        )
    else:
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["workspace_id", "source_key"]
        )
    await db.execute(stmt)

    result = await db.execute(
        select(WorkspaceSource).where(
            WorkspaceSource.workspace_id == ws.workspace_id,
            WorkspaceSource.source_key == source_key,
        )
    )
    row = result.scalar_one()
    payload = WorkspaceSourceSchema(
        workspaceId=str(row.workspace_id),
        sourceKey=row.source_key,
        enabled=row.enabled,
        confidenceOverride=row.confidence_override,
        addedAt=row.added_at,
    )
    return envelope(payload.model_dump(by_alias=True), request_id=get_request_id(request))
