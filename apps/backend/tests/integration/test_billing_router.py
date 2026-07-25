"""The first frontend-facing billing endpoints: GET /billing/plans,
GET /billing/subscription, POST /billing/subscribe. The core requirement is
that subscribe's real "not configured" failure surfaces as a clean 503, not
a raw 500 — proven against the real running app, not mocked."""
from __future__ import annotations

import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.requires_db


@pytest.fixture
def app():
    os.environ.setdefault("DATABASE_URL", os.environ["ORYX_TEST_DB"])
    from oryx.main import create_app

    return create_app()


async def _signed_up_client(app) -> AsyncClient:
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://t")
    body = {
        "email": f"billing-api+{uuid.uuid4().hex[:8]}@oryx.test",
        "password": "StrongPass123",
        "displayName": "Billing API Test",
        "deviceId": str(uuid.uuid4()),
        "deviceLabel": "Pytest Device",
        "devicePlatform": "ios",
    }
    res = await client.post("/v1/auth/signup", json=body)
    assert res.status_code == 200, res.text
    token = res.json()["data"]["tokens"]["accessToken"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


async def test_list_plans_returns_all_18_real_price_points(app) -> None:
    client = await _signed_up_client(app)
    res = await client.get("/v1/billing/plans")
    assert res.status_code == 200, res.text
    plans = res.json()["data"]["plans"]
    assert len(plans) == 18
    plan_ids = {p["planId"] for p in plans}
    assert "focus_monthly_usd" in plan_ids
    assert "vision_yearly_inr" in plan_ids
    focus_monthly_usd = next(p for p in plans if p["planId"] == "focus_monthly_usd")
    assert focus_monthly_usd["tier"] == "focus"
    assert focus_monthly_usd["cadence"] == "monthly"
    assert focus_monthly_usd["currency"] == "USD"
    assert focus_monthly_usd["amount"] == 19.99
    assert all(p["tier"] != "glimpse" for p in plans)


async def test_get_subscription_reflects_default_glimpse_with_no_subscription_row(app) -> None:
    client = await _signed_up_client(app)
    res = await client.get("/v1/billing/subscription")
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["currentPlan"] == "glimpse"
    assert data["subscription"] is None


async def test_subscribe_rejects_unknown_plan_id(app) -> None:
    client = await _signed_up_client(app)
    res = await client.post(
        "/v1/billing/subscribe", json={"planId": "not_a_real_plan", "currency": "USD"}
    )
    assert res.status_code == 422, res.text
    assert res.json()["error"]["code"] == "VALIDATION_FAILED"


async def test_subscribe_rejects_currency_mismatch_with_plan_id(app) -> None:
    client = await _signed_up_client(app)
    res = await client.post(
        "/v1/billing/subscribe", json={"planId": "focus_monthly_usd", "currency": "INR"}
    )
    assert res.status_code == 422, res.text
    assert res.json()["error"]["code"] == "VALIDATION_FAILED"


async def test_subscribe_surfaces_not_configured_as_clean_503_not_a_raw_500(app) -> None:
    """The real, expected outcome today: no live Stripe/Razorpay credentials
    configured, so create_subscription raises PaymentProviderError — this
    must come back as a clean, honest 503 the frontend can render, never an
    unhandled 500."""
    client = await _signed_up_client(app)
    res = await client.post(
        "/v1/billing/subscribe", json={"planId": "focus_monthly_usd", "currency": "USD"}
    )
    assert res.status_code == 503, res.text
    body = res.json()
    assert body["error"]["code"] == "PAYMENT_PROVIDER_UNAVAILABLE"
    assert "details" in body["error"]
    assert body["error"]["details"]["provider"] == "stripe"


async def test_subscribe_routes_inr_to_razorpay_in_the_unavailable_response(app) -> None:
    client = await _signed_up_client(app)
    res = await client.post(
        "/v1/billing/subscribe", json={"planId": "focus_monthly_inr", "currency": "INR"}
    )
    assert res.status_code == 503, res.text
    assert res.json()["error"]["details"]["provider"] == "razorpay"


async def test_get_subscription_reflects_real_subscription_row_after_webhook_event(app) -> None:
    """Ties GET /billing/subscription to the real subscription-state machine
    from the prior billing wave — apply a genuine webhook event through
    BillingService, then confirm the read endpoint reports it."""
    from oryx.core.db import get_sessionmaker
    from oryx.services.billing.service import BillingService

    client = await _signed_up_client(app)
    me = await client.get("/v1/auth/me")
    assert me.status_code == 200, me.text
    workspace_id = uuid.UUID(me.json()["data"]["workspace"]["id"])

    sm = get_sessionmaker()
    async with sm() as session:
        svc = BillingService(session)
        await svc.apply_webhook_event(
            workspace_id=workspace_id,
            provider="stripe",
            provider_subscription_id=f"sub_{uuid.uuid4().hex[:12]}",
            event_type="invoice.paid",
            raw={},
            plan="clarity",
            currency="USD",
        )
        await session.commit()

    res = await client.get("/v1/billing/subscription")
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["currentPlan"] == "clarity"
    assert data["subscription"] == {
        "provider": "stripe",
        "plan": "clarity",
        "status": "active",
        "currency": "USD",
    }
