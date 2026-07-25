"""Applies a verified webhook event onto workspace_subscriptions and, only on
a genuine confirmed-active transition, promotes Workspace.plan.

Never optimistic: creation-time / AFA-pending events (Stripe
subscription.created, Razorpay authenticated/pending) persist as
SubscriptionStatus.PENDING and never touch Workspace.plan. A subscription
whose tier is still unknown (no plan_ref ever seen) never promotes the
workspace either, even on a confirmed ACTIVE event — guessing a tier would
be worse than not enforcing one yet.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.core.models import Workspace
from oryx.services.billing.repository import WorkspaceSubscriptionRepository
from oryx.services.billing.state import SubscriptionStatus, resolve_status


class BillingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = WorkspaceSubscriptionRepository(db)

    async def apply_webhook_event(
        self,
        *,
        workspace_id: uuid.UUID,
        provider: str,
        provider_subscription_id: str,
        event_type: str,
        raw: dict[str, Any],
        plan: str | None = None,
        currency: str | None = None,
    ) -> SubscriptionStatus:
        status = resolve_status(provider=provider, event_type=event_type, raw=raw)

        row = await self.repo.get_by_provider_ref(
            provider=provider, provider_subscription_id=provider_subscription_id
        )
        if row is None:
            row = await self.repo.create(
                workspace_id=workspace_id,
                provider=provider,
                provider_subscription_id=provider_subscription_id,
                plan=plan,
                currency=currency or "USD",
            )
        elif plan is not None and row.plan != plan:
            row.plan = plan
            await self.db.flush()

        await self.repo.update_status(row, status=status.value)

        if status == SubscriptionStatus.ACTIVE and row.plan is not None:
            result = await self.db.execute(
                select(Workspace).where(Workspace.id == row.workspace_id)
            )
            workspace = result.scalar_one_or_none()
            if workspace is not None and workspace.plan != row.plan:
                workspace.plan = row.plan
                await self.db.flush()

        return status
