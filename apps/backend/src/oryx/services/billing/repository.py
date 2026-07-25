"""workspace_subscriptions + plan_prices persistence."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.core.models import PlanPrice, WorkspaceSubscription
from oryx.services.billing.models import PlanPriceRef


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

    async def get_latest_for_workspace(
        self, workspace_id: uuid.UUID
    ) -> WorkspaceSubscription | None:
        """Most recently updated row for this workspace — a workspace could
        in principle have more than one across its history (a lapsed
        subscription, a provider switch); the latest is what GET
        /billing/subscription reports."""
        result = await self.db.execute(
            select(WorkspaceSubscription)
            .where(WorkspaceSubscription.workspace_id == workspace_id)
            .order_by(desc(WorkspaceSubscription.updated_at))
            .limit(1)
        )
        return result.scalar_one_or_none()


def _to_ref(row: PlanPrice) -> PlanPriceRef:
    return PlanPriceRef(
        plan_id=row.plan_id,
        tier=row.tier,
        cadence=row.cadence,
        currency=row.currency,
        amount=row.amount,
        stripe_price_id=row.stripe_price_id,
        razorpay_plan_id=row.razorpay_plan_id,
    )


class PlanPriceRepository:
    """Reads the real plan_prices catalog and converts rows into the
    DB-agnostic PlanPriceRef dataclass core/payment_provider.py resolves
    plan_id against — core/ never queries the DB directly."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, plan_id: str) -> PlanPriceRef | None:
        result = await self.db.execute(
            select(PlanPrice).where(PlanPrice.plan_id == plan_id)
        )
        row = result.scalar_one_or_none()
        return _to_ref(row) if row is not None else None

    async def load_all(self) -> dict[str, PlanPriceRef]:
        """The full catalog as a plan_id -> PlanPriceRef mapping — the shape
        StripeProvider/RazorpayProvider accept as their `pricing` constructor
        argument."""
        result = await self.db.execute(select(PlanPrice))
        return {row.plan_id: _to_ref(row) for row in result.scalars().all()}
