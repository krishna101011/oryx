"""workspace_subscriptions persistence."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.core.models import WorkspaceSubscription


class WorkspaceSubscriptionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_provider_ref(
        self, *, provider: str, provider_subscription_id: str
    ) -> WorkspaceSubscription | None:
        result = await self.db.execute(
            select(WorkspaceSubscription).where(
                WorkspaceSubscription.provider == provider,
                WorkspaceSubscription.provider_subscription_id == provider_subscription_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        workspace_id: uuid.UUID,
        provider: str,
        provider_subscription_id: str,
        plan: str | None,
        currency: str,
    ) -> WorkspaceSubscription:
        row = WorkspaceSubscription(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            provider=provider,
            provider_subscription_id=provider_subscription_id,
            plan=plan,
            currency=currency,
            status="pending",
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def update_status(self, row: WorkspaceSubscription, *, status: str) -> None:
        row.status = status
        row.updated_at = datetime.now(UTC)
        await self.db.flush()
