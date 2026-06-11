"""Dedupe repository.

All operations are scoped to a workspace_id. Service-level checks ensure
no caller can bypass that scope.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from anant.core.models import (
    IntakeDedupeIndex,
    IntakeItemDuplicate,
)


class DedupeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_index(
        self, *, workspace_id: uuid.UUID, fingerprint: str
    ) -> IntakeDedupeIndex | None:
        result = await self.db.execute(
            select(IntakeDedupeIndex).where(
                IntakeDedupeIndex.workspace_id == workspace_id,
                IntakeDedupeIndex.fingerprint == fingerprint,
            )
        )
        return result.scalar_one_or_none()

    async def insert_first_seen(
        self,
        *,
        workspace_id: uuid.UUID,
        fingerprint: str,
        intake_item_id: uuid.UUID,
    ) -> IntakeDedupeIndex:
        stmt = (
            pg_insert(IntakeDedupeIndex)
            .values(
                workspace_id=workspace_id,
                fingerprint=fingerprint,
                first_intake_item_id=intake_item_id,
            )
            .on_conflict_do_nothing(
                index_elements=["workspace_id", "fingerprint"]
            )
            .returning(IntakeDedupeIndex)
        )
        result = await self.db.execute(stmt)
        row = result.scalar_one_or_none()
        if row is not None:
            return row
        existing = await self.get_index(
            workspace_id=workspace_id, fingerprint=fingerprint
        )
        assert existing is not None
        return existing

    async def record_duplicate(
        self,
        *,
        workspace_id: uuid.UUID,
        fingerprint: str,
        intake_source_id: uuid.UUID,
        external_id: str,
    ) -> None:
        dup = IntakeItemDuplicate(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            fingerprint=fingerprint,
            intake_source_id=intake_source_id,
            external_id=external_id,
            observed_at=datetime.now(UTC),
        )
        self.db.add(dup)
        # Bump duplicate_count on the index row
        index = await self.get_index(
            workspace_id=workspace_id, fingerprint=fingerprint
        )
        if index is not None:
            index.duplicate_count = (index.duplicate_count or 0) + 1
        await self.db.flush()
