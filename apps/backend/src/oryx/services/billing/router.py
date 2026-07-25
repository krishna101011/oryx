"""Frontend-facing billing surface — the first real REST API over the
billing foundation (PaymentProvider, plan_prices catalog, subscription
state machine). Distinct from webhook_router.py, which is provider-inbound
only; every endpoint here is authenticated and workspace-scoped.

FOUNDATION-WAVE SCOPE: POST /subscribe calls the real PaymentProvider.
create_subscription, which will raise PaymentProviderError today (no live
vendor credentials, no vendor Price/Plan objects provisioned) — this is
surfaced as a clean 503 PaymentProviderUnavailableError, never a raw 500.
Subscription state itself is never written here; it's driven exclusively
by verified webhook events (services/billing/webhook_router.py +
BillingService), so a successful create_subscription call (once real keys
exist) still waits for the vendor's first webhook to actually promote
anything.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.config import get_settings
from oryx.core.dependencies import (
    ActiveWorkspaceContext,
    db_session,
    envelope,
    get_active_workspace,
    get_request_id,
    require_capability,
)
from oryx.core.errors import PaymentProviderUnavailableError, ValidationError
from oryx.core.models import Workspace
from oryx.core.payment_provider import PaymentProviderError, get_payment_provider
from oryx.services.billing.repository import (
    PlanPriceRepository,
    WorkspaceSubscriptionRepository,
)
from oryx.shared.types import (
    ActiveSubscription,
    PlanPrice,
    PlansResponse,
    SubscribeRequest,
    SubscribeResult,
    SubscriptionSummary,
)

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans")
async def list_plans(
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict:
    catalog = await PlanPriceRepository(db).load_all()
    plans = [
        PlanPrice(
            planId=ref.plan_id,
            tier=ref.tier,
            cadence=ref.cadence,
            currency=ref.currency,
            amount=float(ref.amount),
        )
        for ref in catalog.values()
    ]
    payload = PlansResponse(plans=plans)
    return envelope(payload.model_dump(by_alias=True), request_id=get_request_id(request))


@router.get("/subscription")
async def get_subscription(
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict:
    result = await db.execute(select(Workspace).where(Workspace.id == ws.workspace_id))
    workspace = result.scalar_one()

    row = await WorkspaceSubscriptionRepository(db).get_latest_for_workspace(ws.workspace_id)
    subscription = (
        ActiveSubscription(
            provider=row.provider,
            plan=row.plan,
            status=row.status,
            currency=row.currency,
        )
        if row is not None
        else None
    )
    payload = SubscriptionSummary(currentPlan=workspace.plan, subscription=subscription)
    return envelope(payload.model_dump(by_alias=True), request_id=get_request_id(request))


@router.post("/subscribe", dependencies=[Depends(require_capability("settings.write"))])
async def subscribe(
    body: SubscribeRequest,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict:
    pricing = await PlanPriceRepository(db).load_all()
    plan = pricing.get(body.plan_id)
    if plan is None:
        raise ValidationError(
            "Unknown plan", details={"planId": body.plan_id}
        )
    if plan.currency != body.currency:
        raise ValidationError(
            "currency does not match planId's own currency",
            details={"planId": body.plan_id, "planCurrency": plan.currency, "requestedCurrency": body.currency},
        )

    settings = get_settings()
    provider = get_payment_provider(settings, currency=body.currency, pricing=pricing)
    try:
        handle = await provider.create_subscription(
            customer_ref=str(ws.workspace_id), plan_id=body.plan_id
        )
    except PaymentProviderError as exc:
        raise PaymentProviderUnavailableError(
            details={"provider": exc.provider, "kind": exc.kind.value, "reason": exc.message}
        ) from exc

    payload = SubscribeResult(
        providerSubscriptionId=handle.provider_subscription_id, status=handle.status
    )
    return envelope(payload.model_dump(by_alias=True), request_id=get_request_id(request))
