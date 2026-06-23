"""Publications repository — DB operations only, no business rules.

The unique constraint uq_publications_draft_version_target is the idempotency
guarantee; `ensure_pending` inserts ON CONFLICT DO NOTHING and the caller
re-reads the winning row via `get`.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.core.models import Publication


class PublicationsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(
        self,
        *,
        draft_id: uuid.UUID,
        version_number: int,
        target_id: uuid.UUID,
    ) -> Publication | None:
        result = await self.db.execute(
            select(Publication).where(
                Publication.draft_id == draft_id,
                Publication.version_number == version_number,
                Publication.target_id == target_id,
            )
        )
        return result.scalar_one_or_none()

    async def ensure_pending(
        self,
        *,
        draft_id: uuid.UUID,
        version_number: int,
        target_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> None:
        """Insert a pending row, or do nothing if one already exists for this
        (draft, version, target). Race-safe via the unique constraint — the
        caller re-reads with get() to obtain the winning row."""
        stmt = (
            pg_insert(Publication)
            .values(
                id=uuid.uuid4(),
                draft_id=draft_id,
                version_number=version_number,
                target_id=target_id,
                workspace_id=workspace_id,
                status="pending",
                attempt_count=0,
            )
            .on_conflict_do_nothing(
                constraint="uq_publications_draft_version_target"
            )
        )
        await self.db.execute(stmt)

    async def mark_delivered(
        self,
        *,
        publication_id: uuid.UUID,
        external_id: str | None,
        external_url: str | None,
    ) -> None:
        await self.db.execute(
            update(Publication)
            .where(Publication.id == publication_id)
            .values(
                status="delivered",
                external_id=external_id,
                external_url=external_url,
                error_message=None,
                published_at=datetime.now(UTC),
            )
        )

    async def mark_failed(
        self,
        *,
        publication_id: uuid.UUID,
        error_message: str,
        attempt_count: int | None = None,
    ) -> None:
        values: dict[str, Any] = {"status": "failed", "error_message": error_message}
        if attempt_count is not None:
            values["attempt_count"] = attempt_count
        await self.db.execute(
            update(Publication)
            .where(Publication.id == publication_id)
            .values(**values)
        )

    async def mark_pending_retry(
        self, *, publication_id: uuid.UUID, attempt_count: int, error_message: str
    ) -> None:
        """Transient failure under the attempt ceiling: stay 'pending' (the
        drainer/retry mechanism re-drives it) but record the attempt + error."""
        await self.db.execute(
            update(Publication)
            .where(Publication.id == publication_id)
            .values(
                status="pending",
                attempt_count=attempt_count,
                error_message=error_message,
            )
        )

    async def list_for_workspace(
        self,
        *,
        workspace_id: uuid.UUID,
        status: str | None = None,
        draft_id: uuid.UUID | None = None,
    ) -> list[Publication]:
        stmt = select(Publication).where(Publication.workspace_id == workspace_id)
        if status is not None:
            stmt = stmt.where(Publication.status == status)
        if draft_id is not None:
            stmt = stmt.where(Publication.draft_id == draft_id)
        stmt = stmt.order_by(Publication.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
