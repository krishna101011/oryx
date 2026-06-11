"""Webhook idempotency persistence (CR-4).

The 24h window is enforced by the cleanup job, not by this code path —
this module just records and queries. The TTL semantics live in the
cleanup runbook (architecture §11.5).
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from anant.core.models import WebhookIdempotencyKey

IDEMPOTENCY_TTL = timedelta(hours=24)


class IdempotencyOutcome:
    INSERTED = "inserted"
    DUPLICATE = "duplicate"


class WebhookIdempotencyRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record(
        self,
        *,
        workspace_id: uuid.UUID,
        intake_source_id: uuid.UUID,
        idempotency_key: str,
    ) -> str:
        """Insert; on conflict return DUPLICATE.

        Postgres `ON CONFLICT DO NOTHING ... RETURNING` returns 0 rows on
        conflict and 1 row on insert — that's how we distinguish.
        """
        stmt = (
            pg_insert(WebhookIdempotencyKey)
            .values(
                workspace_id=workspace_id,
                intake_source_id=intake_source_id,
                idempotency_key=idempotency_key,
            )
            .on_conflict_do_nothing(
                index_elements=["workspace_id", "intake_source_id", "idempotency_key"]
            )
            .returning(WebhookIdempotencyKey.idempotency_key)
        )
        result = await self.db.execute(stmt)
        return (
            IdempotencyOutcome.INSERTED
            if result.scalar_one_or_none() is not None
            else IdempotencyOutcome.DUPLICATE
        )

    async def has_seen(
        self,
        *,
        workspace_id: uuid.UUID,
        intake_source_id: uuid.UUID,
        idempotency_key: str,
    ) -> bool:
        result = await self.db.execute(
            select(WebhookIdempotencyKey).where(
                WebhookIdempotencyKey.workspace_id == workspace_id,
                WebhookIdempotencyKey.intake_source_id == intake_source_id,
                WebhookIdempotencyKey.idempotency_key == idempotency_key,
            )
        )
        return result.scalar_one_or_none() is not None

    async def purge_expired(self, *, now: datetime | None = None) -> int:
        """Hourly cleanup job. Returns deleted-row count for observability."""
        cutoff = (now or datetime.now(UTC)) - IDEMPOTENCY_TTL
        result = await self.db.execute(
            delete(WebhookIdempotencyKey).where(
                WebhookIdempotencyKey.seen_at < cutoff
            )
        )
        return result.rowcount or 0
