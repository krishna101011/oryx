"""Intake CRUD + status + manual sync trigger.

The webhook router lives separately (services/intake/webhooks_router.py)
because it has different auth semantics: webhooks rely on HMAC, not
bearer tokens. Keeping the surfaces in different files makes the
permission boundary impossible to confuse.

Pagination uses the Phase 1 cursor envelope. Default page = 50, max = 200.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.core.dependencies import (
    ActiveWorkspaceContext,
    db_session,
    envelope,
    get_active_workspace,
    get_request_id,
    require_capability,
)
from oryx.core.errors import (
    NotFoundError,
    ValidationError,
)
from oryx.core.models import (
    IntakeAuditLog,
    IntakeItem,
    IntakeItemNormalized,
    IntakeSource,
    SourceCatalog,
)
from oryx.core.pagination import decode_cursor, encode_cursor

router = APIRouter(prefix="/intake", tags=["intake"])

# Phase 1 pagination contract
DEFAULT_LIMIT = 50
MAX_LIMIT = 200


# ---------------- pydantic request bodies (router-only) ----------------

class _CreateSourceBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    kind: str
    origin_kind: str   # 'catalog' | 'custom'
    origin_catalog_key: str | None = None
    origin_custom_id: str | None = None
    config: dict[str, Any] = {}


class _PatchSourceBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    enabled: bool | None = None
    config: dict[str, Any] | None = None


# ---------------- helpers ----------------

def _source_to_dict(s: IntakeSource) -> dict[str, Any]:
    return {
        "id": str(s.id),
        "workspaceId": str(s.workspace_id),
        "kind": s.kind,
        "name": s.name,
        "enabled": s.enabled,
        "config": s.config,
        "health": s.status,
        "lastSyncedAt": s.last_synced_at.isoformat() if s.last_synced_at else None,
        "consecutiveFailures": s.consecutive_failures,
        "originKind": s.origin_kind,
        "originCatalogKey": s.origin_catalog_key,
        "originCustomId": str(s.origin_custom_id) if s.origin_custom_id else None,
    }


def _audit_to_dict(a: IntakeAuditLog) -> dict[str, Any]:
    return {
        "id": str(a.id),
        "intakeSourceId": str(a.intake_source_id) if a.intake_source_id else None,
        "event": a.event,
        "data": a.data,
        "createdAt": a.created_at.isoformat(),
    }


def _clamp_limit(limit: int | None) -> int:
    if limit is None:
        return DEFAULT_LIMIT
    if limit < 1:
        return 1
    if limit > MAX_LIMIT:
        return MAX_LIMIT
    return limit


# ---------------- endpoints ----------------

@router.post(
    "/sources",
    dependencies=[Depends(require_capability("intake.write"))],
)
async def create_source(
    body: _CreateSourceBody,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict:
    # Provider-specific config validation lives behind a per-kind table.
    # Batch 2 only RSS is implemented; other kinds will be added as their
    # providers ship.
    if body.kind not in {"rss", "gmail", "webhook", "api_pull", "manual"}:
        raise ValidationError(details={"reason": "unsupported_kind"})
    if body.origin_kind not in {"catalog", "custom"}:
        raise ValidationError(details={"reason": "invalid_origin_kind"})

    name = body.name
    kind = body.kind
    config = body.config

    # Catalog activation (source-governance follow-up wave): the ONLY real
    # path today that turns a source_catalog entry into a real intake
    # source — this was previously accepted by the request schema but never
    # actually exercised in production. `name`/`kind`/`config.feed_url` are
    # NOT trusted from the client here: the server derives them from the
    # real catalog row so a caller can't claim origin_catalog_key="coindesk"
    # while pointing feed_url at something else. Cadence overrides
    # (fetch_interval_minutes etc.) in the request config still pass
    # through — catalog-backed sources "inherit feed_url and only edit
    # polling cadence" per providers/rss/config_schema.py's own doc comment.
    if body.origin_kind == "catalog":
        if not body.origin_catalog_key:
            raise ValidationError(details={"reason": "missing_origin_catalog_key"})
        catalog_row = await db.get(SourceCatalog, body.origin_catalog_key)
        if catalog_row is None:
            raise NotFoundError("Catalog source not found")
        name = catalog_row.name
        kind = "rss"
        config = {**body.config, "feed_url": catalog_row.url}

    # Light per-kind validation; full vendor validation done by the provider
    # at sync time (Batch 2 Wave A only wires RSS here).
    if kind == "rss":
        from oryx.services.intake.providers.rss import RssProvider
        validation = await RssProvider().validate_config(config)
        if validation.status.value != "ok":
            raise ValidationError(
                details={"reason": "invalid_rss_config", "message": validation.message}
            )

    src = IntakeSource(
        id=uuid.uuid4(),
        workspace_id=ws.workspace_id,
        kind=kind,
        name=name,
        enabled=True,
        config=config,
        origin_kind=body.origin_kind,
        origin_catalog_key=body.origin_catalog_key,
        origin_custom_id=uuid.UUID(body.origin_custom_id) if body.origin_custom_id else None,
        status="healthy",
    )
    db.add(src)
    await db.flush()

    db.add(
        IntakeAuditLog(
            id=uuid.uuid4(),
            workspace_id=ws.workspace_id,
            intake_source_id=src.id,
            event="config_changed",
            data={"action": "created", "kind": body.kind},
        )
    )

    return envelope(
        _source_to_dict(src), request_id=get_request_id(request)
    )


@router.get(
    "/sources",
    dependencies=[Depends(require_capability("intake.read"))],
)
async def list_sources(
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=DEFAULT_LIMIT, le=MAX_LIMIT),
) -> dict:
    limit = _clamp_limit(limit)
    stmt = (
        select(IntakeSource)
        .where(
            IntakeSource.workspace_id == ws.workspace_id,
            IntakeSource.deleted_at.is_(None),
        )
        .order_by(desc(IntakeSource.created_at))
        .limit(limit + 1)
    )
    if cursor:
        decoded = decode_cursor(cursor)
        before = datetime.fromisoformat(decoded["created_at"])
        stmt = stmt.where(IntakeSource.created_at < before)

    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    has_more = len(rows) > limit
    rows = rows[:limit]

    next_cursor = None
    if has_more and rows:
        next_cursor = encode_cursor({"created_at": rows[-1].created_at.isoformat()})

    return envelope(
        [_source_to_dict(r) for r in rows],
        request_id=get_request_id(request),
        pagination={"nextCursor": next_cursor, "prevCursor": None},
    )


@router.get(
    "/sources/{source_id}",
    dependencies=[Depends(require_capability("intake.read"))],
)
async def get_source(
    source_id: uuid.UUID,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict:
    row = await _load_source(db, ws.workspace_id, source_id)
    return envelope(_source_to_dict(row), request_id=get_request_id(request))


@router.patch(
    "/sources/{source_id}",
    dependencies=[Depends(require_capability("intake.write"))],
)
async def patch_source(
    source_id: uuid.UUID,
    body: _PatchSourceBody,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict:
    row = await _load_source(db, ws.workspace_id, source_id)
    if body.name is not None:
        row.name = body.name
    if body.enabled is not None:
        row.enabled = body.enabled
    if body.config is not None:
        row.config = body.config
    row.updated_at = datetime.now(UTC)
    db.add(
        IntakeAuditLog(
            id=uuid.uuid4(),
            workspace_id=ws.workspace_id,
            intake_source_id=row.id,
            event="config_changed",
            data=body.model_dump(exclude_unset=True),
        )
    )
    await db.flush()
    return envelope(_source_to_dict(row), request_id=get_request_id(request))


@router.delete(
    "/sources/{source_id}",
    dependencies=[Depends(require_capability("intake.write"))],
)
async def delete_source(
    source_id: uuid.UUID,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict:
    row = await _load_source(db, ws.workspace_id, source_id)
    row.deleted_at = datetime.now(UTC)
    row.status = "disabled"
    db.add(
        IntakeAuditLog(
            id=uuid.uuid4(),
            workspace_id=ws.workspace_id,
            intake_source_id=row.id,
            event="config_changed",
            data={"action": "deleted"},
        )
    )
    await db.flush()
    # NOTE: upstream credential revoke happens in a separate worker so an
    # API request never blocks on a vendor endpoint. Wave E wires that.
    return envelope({"ok": True}, request_id=get_request_id(request))


@router.post(
    "/sources/{source_id}/sync",
    dependencies=[Depends(require_capability("intake.write"))],
)
async def manual_sync(
    source_id: uuid.UUID,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict:
    row = await _load_source(db, ws.workspace_id, source_id)
    # Phase 3 Batch 2 — we record the trigger; the scheduler (Wave E) does
    # the actual fetch. This keeps the API non-blocking.
    db.add(
        IntakeAuditLog(
            id=uuid.uuid4(),
            workspace_id=ws.workspace_id,
            intake_source_id=row.id,
            event="manual_sync_requested",
            data={},
        )
    )
    # Reset the next attempt to "now" so the scheduler picks it up promptly.
    row.last_attempt_at = None
    await db.flush()
    return envelope({"queued": True}, request_id=get_request_id(request))


@router.get(
    "/sources/{source_id}/audit",
    dependencies=[Depends(require_capability("intake.read"))],
)
async def get_audit(
    source_id: uuid.UUID,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=DEFAULT_LIMIT, le=MAX_LIMIT),
) -> dict:
    # ensure source belongs to workspace before exposing audit
    await _load_source(db, ws.workspace_id, source_id)
    limit = _clamp_limit(limit)
    stmt = (
        select(IntakeAuditLog)
        .where(
            IntakeAuditLog.workspace_id == ws.workspace_id,
            IntakeAuditLog.intake_source_id == source_id,
        )
        .order_by(desc(IntakeAuditLog.created_at))
        .limit(limit + 1)
    )
    if cursor:
        decoded = decode_cursor(cursor)
        before = datetime.fromisoformat(decoded["created_at"])
        stmt = stmt.where(IntakeAuditLog.created_at < before)

    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    has_more = len(rows) > limit
    rows = rows[:limit]

    next_cursor = None
    if has_more and rows:
        next_cursor = encode_cursor({"created_at": rows[-1].created_at.isoformat()})

    return envelope(
        [_audit_to_dict(r) for r in rows],
        request_id=get_request_id(request),
        pagination={"nextCursor": next_cursor, "prevCursor": None},
    )


@router.get(
    "/items/recent",
    dependencies=[Depends(require_capability("intake.read"))],
)
async def recent_items(
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
    limit: int = Query(default=10, ge=1, le=50),
) -> dict:
    """The Command Center "Today" feed — the most recently ingested items with
    their REAL content (normalized subject + source name), newest first.

    The activity_inbox row for an ingest is a generic "New item ingested"
    notification carrying only ids; this endpoint is what lets the dashboard
    show what actually came in. The normalized row is outer-joined: an item the
    normalizer hasn't reached yet still appears (subject null), so the feed
    never under-reports fresh ingests.
    """
    stmt = (
        select(
            IntakeItem.id,
            IntakeItem.provider_name,
            IntakeItem.received_at,
            IntakeItemNormalized.subject,
            IntakeSource.name,
        )
        .join(IntakeSource, IntakeSource.id == IntakeItem.intake_source_id)
        .outerjoin(
            IntakeItemNormalized,
            IntakeItemNormalized.intake_item_id == IntakeItem.id,
        )
        .where(
            IntakeItem.workspace_id == ws.workspace_id,
            IntakeItem.deleted_at.is_(None),
        )
        .order_by(desc(IntakeItem.received_at))
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    payload = [
        {
            "id": str(item_id),
            "subject": subject,
            "sourceName": source_name,
            "providerName": provider_name,
            "receivedAt": received_at.isoformat(),
        }
        for item_id, provider_name, received_at, subject, source_name in rows
    ]
    return envelope(payload, request_id=get_request_id(request))


@router.get(
    "/items/{item_id}",
    dependencies=[Depends(require_capability("intake.read"))],
)
async def get_item(
    item_id: uuid.UUID,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict:
    """One ingested item with its real content — what an Activity "New item
    ingested" row (whose payload carries intakeItemId) and a search result
    open onto: headline, source, sender, body text, and extracted links.

    Same outer-join contract as /items/recent: an item the normalizer hasn't
    reached yet still resolves (subject/body/links empty), it never 404s just
    for being un-normalized. Declared AFTER /items/recent so the literal
    route keeps winning.
    """
    stmt = (
        select(IntakeItem, IntakeItemNormalized, IntakeSource.name)
        .join(IntakeSource, IntakeSource.id == IntakeItem.intake_source_id)
        .outerjoin(
            IntakeItemNormalized,
            IntakeItemNormalized.intake_item_id == IntakeItem.id,
        )
        .where(
            IntakeItem.id == item_id,
            IntakeItem.workspace_id == ws.workspace_id,
            IntakeItem.deleted_at.is_(None),
        )
    )
    row = (await db.execute(stmt)).one_or_none()
    if row is None:
        raise NotFoundError("Item not found")
    item, normalized, source_name = row
    payload = {
        "id": str(item.id),
        "subject": normalized.subject if normalized else None,
        "bodyText": normalized.body_text if normalized else None,
        "senderLabel": normalized.sender_label if normalized else None,
        "senderDomain": normalized.sender_domain if normalized else None,
        # normalized.links is JSONB [{url, anchor}] written by the normalizer.
        "links": normalized.links if normalized else [],
        "sourceName": source_name,
        "providerName": item.provider_name,
        "receivedAt": item.received_at.isoformat(),
    }
    return envelope(payload, request_id=get_request_id(request))


@router.get(
    "/status",
    dependencies=[Depends(require_capability("intake.read"))],
)
async def status_summary(
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict:
    # Group counts by status — one round-trip
    stmt = (
        select(IntakeSource.status, func.count())
        .where(
            IntakeSource.workspace_id == ws.workspace_id,
            IntakeSource.deleted_at.is_(None),
        )
        .group_by(IntakeSource.status)
    )
    result = await db.execute(stmt)
    by_health = {"healthy": 0, "degraded": 0, "auth_required": 0, "disabled": 0}
    total = 0
    for status_val, count in result.all():
        by_health[status_val] = count
        total += count
    return envelope(
        {"total": total, "byHealth": by_health},
        request_id=get_request_id(request),
    )


# ---------------- helpers ----------------

async def _load_source(
    db: AsyncSession, workspace_id: uuid.UUID, source_id: uuid.UUID
) -> IntakeSource:
    result = await db.execute(
        select(IntakeSource).where(
            IntakeSource.id == source_id,
            IntakeSource.workspace_id == workspace_id,
            IntakeSource.deleted_at.is_(None),
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise NotFoundError("Source not found")
    return row
