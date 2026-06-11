"""Platform-admin intake operations — dead-letter ops surface (§12.3, §14.2)
and manual ingest (CR-8).

Every endpoint here is gated by `require_platform_admin` (§17.4
`intake.platform`): an account-level flag, never a workspace role.
Workspace owners and admins must not pass.
"""
from __future__ import annotations

import hashlib
import time
import uuid
from collections import defaultdict, deque
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from anant.config import get_settings
from anant.core.dependencies import (
    db_session,
    envelope,
    get_request_id,
    require_platform_admin,
)
from anant.core.errors import NotFoundError, RateLimitedError, ValidationError
from anant.core.logging import get_logger
from anant.core.models import Account, IntakeAuditLog, IntakeSource, OutboxDeadLetter, Workspace
from anant.core.pagination import decode_cursor, encode_cursor
from anant.services.intake.providers.base import RawItem
from anant.services.intake.service import IntakeService
from anant.services.normalization.url_canonicalizer import canonicalize_url
from anant.services.queue.dead_letter import (
    discard_dead_letter,
    get_dead_letter,
    replay_dead_letter,
)

logger = get_logger(__name__)

router = APIRouter(
    prefix="/admin/intake",
    tags=["intake-admin"],
    dependencies=[Depends(require_platform_admin)],
)

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


def _dead_letter_to_dict(row: OutboxDeadLetter) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "originalId": str(row.original_id),
        "eventName": row.event_name,
        "workspaceId": str(row.workspace_id) if row.workspace_id else None,
        "movedAt": row.moved_at.isoformat(),
        "finalError": row.final_error,
        "totalAttempts": row.total_attempts,
    }


@router.get("/dead-letter")
async def list_dead_letter_entries(
    request: Request,
    db: AsyncSession = Depends(db_session),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
) -> dict[str, Any]:
    stmt = (
        select(OutboxDeadLetter)
        .order_by(desc(OutboxDeadLetter.moved_at))
        .limit(limit + 1)
    )
    if cursor:
        decoded = decode_cursor(cursor)
        before = datetime.fromisoformat(decoded["moved_at"])
        stmt = stmt.where(OutboxDeadLetter.moved_at < before)

    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    has_more = len(rows) > limit
    rows = rows[:limit]

    next_cursor = None
    if has_more and rows:
        next_cursor = encode_cursor({"moved_at": rows[-1].moved_at.isoformat()})

    return envelope(
        [_dead_letter_to_dict(r) for r in rows],
        request_id=get_request_id(request),
        pagination={"nextCursor": next_cursor, "prevCursor": None},
    )


@router.post("/dead-letter/{dead_letter_id}/replay")
async def replay_dead_letter_entry(
    dead_letter_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(db_session),
) -> dict[str, Any]:
    row = await get_dead_letter(db, dead_letter_id)
    if row is None:
        raise NotFoundError("Dead-letter entry not found")
    outbox_id = await replay_dead_letter(db, row=row)
    logger.info(
        "dead_letter.replayed",
        extra={
            "dead_letter_id": str(dead_letter_id),
            "event_name": row.event_name,
            "outbox_id": str(outbox_id),
        },
    )
    return envelope(
        {"replayed": True, "outboxEventId": str(outbox_id)},
        request_id=get_request_id(request),
    )


@router.post("/dead-letter/{dead_letter_id}/discard")
async def discard_dead_letter_entry(
    dead_letter_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(db_session),
) -> dict[str, Any]:
    row = await get_dead_letter(db, dead_letter_id)
    if row is None:
        raise NotFoundError("Dead-letter entry not found")
    await discard_dead_letter(db, row=row)
    logger.info(
        "dead_letter.discarded",
        extra={
            "dead_letter_id": str(dead_letter_id),
            "event_name": row.event_name,
            "final_error": row.final_error[:200],
        },
    )
    return envelope({"discarded": True}, request_id=get_request_id(request))


# ---------------------------------------------------------------------------
# Manual ingest — CR-8
# ---------------------------------------------------------------------------

# Same in-memory sliding-window pattern as Phase 2's RateLimitMiddleware:
# per-process is acceptable at Phase 3 scale, keyed per admin account.
_manual_ingest_hits: dict[str, deque[float]] = defaultdict(deque)
_MANUAL_INGEST_WINDOW_SECONDS = 60.0


def _manual_ingest_rate_ok(account_id: str, limit: int) -> bool:
    now = time.time()
    bucket = _manual_ingest_hits[account_id]
    while bucket and now - bucket[0] > _MANUAL_INGEST_WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= limit:
        return False
    bucket.append(now)
    return True


class _ManualIngestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    title: str
    url: str | None = None
    body_text: str | None = None
    sender: str | None = None


def _manual_external_id(body: _ManualIngestBody) -> str:
    """Deterministic so a re-submission of the same content hits the
    provider-key dedupe instead of creating a second raw record."""
    if body.url:
        basis = canonicalize_url(body.url)
    else:
        basis = f"{body.title}\n{body.body_text or ''}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


@router.post("/manual_ingest")
async def manual_ingest(
    body: _ManualIngestBody,
    request: Request,
    db: AsyncSession = Depends(db_session),
    admin: Account = Depends(require_platform_admin),
) -> dict[str, Any]:
    settings = get_settings()
    if not _manual_ingest_rate_ok(str(admin.id), settings.manual_ingest_per_minute):
        raise RateLimitedError(details={"retryAfterSeconds": 60})
    if not body.url and not body.body_text:
        raise ValidationError(details={"reason": "url_or_body_text_required"})

    workspace_id = uuid.UUID(body.workspace_id)
    workspace = await db.get(Workspace, workspace_id)
    if workspace is None or workspace.deleted_at is not None:
        raise NotFoundError("Workspace not found")

    # One operational kind='manual' source per workspace, created on first use.
    result = await db.execute(
        select(IntakeSource).where(
            IntakeSource.workspace_id == workspace_id,
            IntakeSource.kind == "manual",
            IntakeSource.deleted_at.is_(None),
        )
    )
    source = result.scalars().first()
    if source is None:
        source = IntakeSource(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            kind="manual",
            name="Manual ingest",
            enabled=True,
            config={},
            origin_kind="custom",
            status="healthy",
        )
        db.add(source)
        await db.flush()

    raw = RawItem(
        external_id=_manual_external_id(body),
        received_at=datetime.now(UTC),
        sender=body.sender or "manual-ingest",
        subject=body.title,
        body_text=body.body_text,
        body_html=None,
        links=[{"url": body.url, "anchor": body.title}] if body.url else [],
        payload={
            "manual": True,
            "submittedBy": str(admin.id),
            "title": body.title,
            "url": body.url,
            "bodyText": body.body_text,
        },
    )

    # Full pipeline — normalize → dedupe → persist → outbox. No shortcuts:
    # a manually ingested item is indistinguishable downstream.
    service = IntakeService(db)
    ingest = await service.ingest_raw_item(
        workspace_id=workspace_id,
        intake_source_id=source.id,
        provider_name="manual",
        raw=raw,
    )

    db.add(
        IntakeAuditLog(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            intake_source_id=source.id,
            event="manual_ingest",
            data={
                "admin_account_id": str(admin.id),
                "outcome": ingest.outcome.value,
                "fingerprint": ingest.fingerprint,
            },
        )
    )
    await db.flush()

    return envelope(
        {
            "outcome": ingest.outcome.value,
            "intakeItemId": str(ingest.intake_item_id) if ingest.intake_item_id else None,
            "fingerprint": ingest.fingerprint,
        },
        request_id=get_request_id(request),
    )
