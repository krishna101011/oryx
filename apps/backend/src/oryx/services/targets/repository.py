"""Publish-targets repository — DB operations only, no business rules.

The only place that touches the publish_targets table. Credentials are stored
as opaque AES-256-GCM ciphertext/IV (encryption happens in the service layer
before insert); this layer never decrypts.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.core.models import PublishTarget


class TargetsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def insert(
        self,
        *,
        workspace_id: uuid.UUID,
        name: str,
        channel: str,
        credentials: bytes,
        credentials_iv: bytes,
        config: dict[str, Any],
    ) -> PublishTarget:
        row = PublishTarget(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            name=name,
            channel=channel,
            credentials=credentials,
            credentials_iv=credentials_iv,
            config=config or {},
            is_active=True,
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def get(
        self, *, workspace_id: uuid.UUID, target_id: uuid.UUID
    ) -> PublishTarget | None:
        result = await self.db.execute(
            select(PublishTarget).where(
                PublishTarget.id == target_id,
                PublishTarget.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_workspace(
        self, workspace_id: uuid.UUID
    ) -> list[PublishTarget]:
        result = await self.db.execute(
            select(PublishTarget)
            .where(PublishTarget.workspace_id == workspace_id)
            .order_by(PublishTarget.created_at)
        )
        return list(result.scalars().all())

    async def set_health(
        self,
        *,
        target_id: uuid.UUID,
        ok: bool,
        at: datetime | None = None,
    ) -> None:
        await self.db.execute(
            update(PublishTarget)
            .where(PublishTarget.id == target_id)
            .values(last_health_ok=ok, last_health_at=at or datetime.now(UTC))
        )

    async def delete(self, *, target_id: uuid.UUID) -> None:
        row = await self.db.get(PublishTarget, target_id)
        if row is not None:
            await self.db.delete(row)
            await self.db.flush()
