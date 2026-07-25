"""Public inbound billing webhook endpoints (Stripe + Razorpay).

NO bearer auth — same posture as intake's webhooks_router.py. Security is
entirely from vendor signature verification, which is the FIRST thing every
handler below does: nothing about the payload (including its own claimed
subscription id) is trusted until verify_webhook() returns cleanly. This
file is public-internet-facing; treat changes to the ordering below as a
security review, not a refactor.

Foundation-wave scope: if the vendor payload has no workspace_id in its
metadata/notes (expected until the checkout flow that stashes it exists),
the handler verifies the signature, records nothing, and returns 200 —
webhook contracts require a 2xx even when there is nothing yet to apply, so
the vendor does not retry indefinitely.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from oryx.config import get_settings
from oryx.core.dependencies import db_session, envelope, get_request_id
from oryx.core.payment_provider import (
    PaymentProviderError,
    get_razorpay_provider,
    get_stripe_provider,
)
from oryx.services.billing.service import BillingService

router = APIRouter(prefix="/billing/webhooks", tags=["billing-webhook"])


def _rejection(request: Request) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={
            "error": {
                "code": "AUTH_REQUIRED",
                "message": "Webhook signature verification failed",
                "requestId": get_request_id(request),
            }
        },
    )


async def _apply(request: Request, db: AsyncSession, provider_name: str, event) -> dict:
    if event.workspace_ref is None:
        return envelope(
            {"applied": False, "reason": "no_workspace_ref"},
            request_id=get_request_id(request),
        )
    try:
        workspace_id = uuid.UUID(event.workspace_ref)
    except ValueError:
        return envelope(
            {"applied": False, "reason": "invalid_workspace_ref"},
            request_id=get_request_id(request),
        )

    svc = BillingService(db)
    status = await svc.apply_webhook_event(
        workspace_id=workspace_id,
        provider=provider_name,
        provider_subscription_id=event.provider_subscription_id or "",
        event_type=event.event_type,
        raw=event.raw,
        plan=event.plan_ref,
    )
    await db.commit()
    return envelope(
        {"applied": True, "status": status.value},
        request_id=get_request_id(request),
    )


# response_model=None: the `dict | JSONResponse` union is not a valid pydantic
# field (same reason intake's webhooks_router.py disables it).
@router.post("/stripe", response_model=None)
async def receive_stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(db_session),
) -> dict | JSONResponse:
    raw_body = await request.body()
    try:
        event = get_stripe_provider(get_settings()).verify_webhook(
            headers=request.headers, body=raw_body
        )
    except PaymentProviderError:
        return _rejection(request)
    return await _apply(request, db, "stripe", event)


@router.post("/razorpay", response_model=None)
async def receive_razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(db_session),
) -> dict | JSONResponse:
    raw_body = await request.body()
    try:
        event = get_razorpay_provider(get_settings()).verify_webhook(
            headers=request.headers, body=raw_body
        )
    except PaymentProviderError:
        return _rejection(request)
    return await _apply(request, db, "razorpay", event)
