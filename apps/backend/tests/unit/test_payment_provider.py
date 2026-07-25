"""core/payment_provider.py — signature verification is the security boundary
for both vendors' webhook endpoints; these tests forge and tamper with real
payloads the same way an attacker would, not just format-check the code path.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from decimal import Decimal

import pytest

from oryx.core.payment_provider import (
    PaymentProviderError,
    PaymentProviderErrorKind,
    RazorpayProvider,
    StripeProvider,
    get_payment_provider,
    get_razorpay_provider,
    get_stripe_provider,
)
from oryx.services.billing.models import PlanPriceRef

# ============================================================================
# Stripe
# ============================================================================


def _stripe_sign(secret: str, ts: int, body: bytes) -> str:
    signed_payload = f"{ts}.".encode("ascii") + body
    digest = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"t={ts},v1={digest}"


def _stripe_body(event_type: str = "customer.subscription.created", **object_fields) -> bytes:
    payload = {
        "type": event_type,
        "data": {
            "object": {
                "id": "sub_123",
                "metadata": {"workspace_id": "ws-1", "workspace_plan": "focus"},
                **object_fields,
            }
        },
    }
    return json.dumps(payload).encode("utf-8")


def test_stripe_verify_accepts_genuine_signature() -> None:
    secret = "whsec_test_secret"
    body = _stripe_body()
    ts = int(time.time())
    header = _stripe_sign(secret, ts, body)
    provider = StripeProvider(api_key=None, webhook_secret=secret)
    event = provider.verify_webhook(headers={"Stripe-Signature": header}, body=body)
    assert event.event_type == "customer.subscription.created"
    assert event.provider_subscription_id == "sub_123"
    assert event.workspace_ref == "ws-1"
    assert event.plan_ref == "focus"


def test_stripe_verify_rejects_tampered_body() -> None:
    """The attacker changes the body after a genuine signature was issued for
    the original payload — e.g. trying to redirect the event to a different
    workspace_id without knowing the webhook secret."""
    secret = "whsec_test_secret"
    original_body = _stripe_body()
    ts = int(time.time())
    header = _stripe_sign(secret, ts, original_body)

    tampered = json.loads(original_body)
    tampered["data"]["object"]["metadata"]["workspace_id"] = "attacker-ws"
    tampered_body = json.dumps(tampered).encode("utf-8")

    provider = StripeProvider(api_key=None, webhook_secret=secret)
    with pytest.raises(PaymentProviderError) as exc:
        provider.verify_webhook(headers={"Stripe-Signature": header}, body=tampered_body)
    assert exc.value.kind == PaymentProviderErrorKind.SIGNATURE_INVALID


def test_stripe_verify_rejects_signature_from_wrong_secret() -> None:
    """Simulates an attacker who knows the payload shape but not our secret —
    forges a self-consistent signature with a guessed/different key."""
    body = _stripe_body()
    ts = int(time.time())
    forged_header = _stripe_sign("attacker-guessed-secret", ts, body)

    provider = StripeProvider(api_key=None, webhook_secret="whsec_real_secret")
    with pytest.raises(PaymentProviderError) as exc:
        provider.verify_webhook(headers={"Stripe-Signature": forged_header}, body=body)
    assert exc.value.kind == PaymentProviderErrorKind.SIGNATURE_INVALID


def test_stripe_verify_rejects_replayed_old_timestamp() -> None:
    secret = "whsec_test_secret"
    body = _stripe_body()
    stale_ts = int(time.time()) - 3600  # 1h old, well outside the 300s tolerance
    header = _stripe_sign(secret, stale_ts, body)

    provider = StripeProvider(api_key=None, webhook_secret=secret)
    with pytest.raises(PaymentProviderError) as exc:
        provider.verify_webhook(headers={"Stripe-Signature": header}, body=body)
    assert exc.value.kind == PaymentProviderErrorKind.SIGNATURE_INVALID


def test_stripe_verify_rejects_missing_header() -> None:
    provider = StripeProvider(api_key=None, webhook_secret="whsec_test_secret")
    with pytest.raises(PaymentProviderError) as exc:
        provider.verify_webhook(headers={}, body=_stripe_body())
    assert exc.value.kind == PaymentProviderErrorKind.SIGNATURE_INVALID


def test_stripe_verify_rejects_when_secret_not_configured() -> None:
    provider = StripeProvider(api_key=None, webhook_secret=None)
    with pytest.raises(PaymentProviderError) as exc:
        provider.verify_webhook(
            headers={"Stripe-Signature": "t=1,v1=deadbeef"}, body=b"{}"
        )
    assert exc.value.kind == PaymentProviderErrorKind.PERMANENT


def test_stripe_verify_resolves_updated_event_status_from_object() -> None:
    secret = "whsec_test_secret"
    body = _stripe_body("customer.subscription.updated", status="active")
    ts = int(time.time())
    header = _stripe_sign(secret, ts, body)
    provider = StripeProvider(api_key=None, webhook_secret=secret)
    event = provider.verify_webhook(headers={"Stripe-Signature": header}, body=body)
    assert event.raw["data"]["object"]["status"] == "active"


# ============================================================================
# Razorpay
# ============================================================================


def _razorpay_sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def _razorpay_body(event: str = "subscription.activated") -> bytes:
    payload = {
        "event": event,
        "payload": {
            "subscription": {
                "entity": {
                    "id": "sub_abc",
                    "notes": {"workspace_id": "ws-2", "workspace_plan": "clarity"},
                }
            }
        },
    }
    return json.dumps(payload).encode("utf-8")


def test_razorpay_verify_accepts_genuine_signature() -> None:
    secret = "razorpay_test_secret"
    body = _razorpay_body()
    header = _razorpay_sign(secret, body)
    provider = RazorpayProvider(key_id=None, key_secret=None, webhook_secret=secret)
    event = provider.verify_webhook(headers={"X-Razorpay-Signature": header}, body=body)
    assert event.event_type == "subscription.activated"
    assert event.provider_subscription_id == "sub_abc"
    assert event.workspace_ref == "ws-2"
    assert event.plan_ref == "clarity"


def test_razorpay_verify_rejects_tampered_body() -> None:
    secret = "razorpay_test_secret"
    original_body = _razorpay_body()
    header = _razorpay_sign(secret, original_body)

    tampered = json.loads(original_body)
    tampered["payload"]["subscription"]["entity"]["notes"]["workspace_plan"] = "vision"
    tampered_body = json.dumps(tampered).encode("utf-8")

    provider = RazorpayProvider(key_id=None, key_secret=None, webhook_secret=secret)
    with pytest.raises(PaymentProviderError) as exc:
        provider.verify_webhook(headers={"X-Razorpay-Signature": header}, body=tampered_body)
    assert exc.value.kind == PaymentProviderErrorKind.SIGNATURE_INVALID


def test_razorpay_verify_rejects_signature_from_wrong_secret() -> None:
    body = _razorpay_body()
    forged_header = _razorpay_sign("attacker-guessed-secret", body)
    provider = RazorpayProvider(
        key_id=None, key_secret=None, webhook_secret="razorpay_real_secret"
    )
    with pytest.raises(PaymentProviderError) as exc:
        provider.verify_webhook(headers={"X-Razorpay-Signature": forged_header}, body=body)
    assert exc.value.kind == PaymentProviderErrorKind.SIGNATURE_INVALID


def test_razorpay_verify_rejects_missing_header() -> None:
    provider = RazorpayProvider(
        key_id=None, key_secret=None, webhook_secret="razorpay_test_secret"
    )
    with pytest.raises(PaymentProviderError) as exc:
        provider.verify_webhook(headers={}, body=_razorpay_body())
    assert exc.value.kind == PaymentProviderErrorKind.SIGNATURE_INVALID


def test_razorpay_verify_rejects_when_secret_not_configured() -> None:
    provider = RazorpayProvider(key_id=None, key_secret=None, webhook_secret=None)
    with pytest.raises(PaymentProviderError) as exc:
        provider.verify_webhook(
            headers={"X-Razorpay-Signature": "deadbeef"}, body=b"{}"
        )
    assert exc.value.kind == PaymentProviderErrorKind.PERMANENT


# ============================================================================
# Factory
# ============================================================================


class _FakeSettings:
    stripe_api_key = "sk_test"
    stripe_webhook_secret = "whsec_test"
    razorpay_key_id = "rzp_test_id"
    razorpay_key_secret = "rzp_test_secret"
    razorpay_webhook_secret = "rzp_whsec_test"


def test_factory_routes_inr_to_razorpay() -> None:
    provider = get_payment_provider(_FakeSettings(), currency="INR")
    assert provider.name == "razorpay"


def test_factory_routes_inr_case_insensitively() -> None:
    provider = get_payment_provider(_FakeSettings(), currency="inr")
    assert provider.name == "razorpay"


@pytest.mark.parametrize("currency", ["USD", "EUR", "GBP"])
def test_factory_routes_non_inr_to_stripe(currency: str) -> None:
    provider = get_payment_provider(_FakeSettings(), currency=currency)
    assert provider.name == "stripe"


def test_get_stripe_provider_and_get_razorpay_provider_read_settings() -> None:
    stripe = get_stripe_provider(_FakeSettings())
    razorpay = get_razorpay_provider(_FakeSettings())
    assert stripe.name == "stripe"
    assert razorpay.name == "razorpay"


# ============================================================================
# create_subscription — plan_id resolution against the pricing catalog
# ============================================================================

_FOCUS_MONTHLY_USD = PlanPriceRef(
    plan_id="focus_monthly_usd",
    tier="focus",
    cadence="monthly",
    currency="USD",
    amount=Decimal("19.99"),
    stripe_price_id=None,
    razorpay_plan_id=None,
)


async def test_stripe_create_subscription_rejects_unconfigured_api_key() -> None:
    provider = StripeProvider(
        api_key=None, webhook_secret=None, pricing={"focus_monthly_usd": _FOCUS_MONTHLY_USD}
    )
    with pytest.raises(PaymentProviderError) as exc:
        await provider.create_subscription(customer_ref="cus_1", plan_id="focus_monthly_usd")
    assert exc.value.kind == PaymentProviderErrorKind.PERMANENT
    assert "STRIPE_API_KEY" in exc.value.message


async def test_stripe_create_subscription_rejects_unknown_plan_id() -> None:
    provider = StripeProvider(api_key="sk_test", webhook_secret=None, pricing={})
    with pytest.raises(PaymentProviderError) as exc:
        await provider.create_subscription(customer_ref="cus_1", plan_id="not_a_real_plan")
    assert exc.value.kind == PaymentProviderErrorKind.PERMANENT
    assert "Unknown plan_id" in exc.value.message


async def test_stripe_create_subscription_resolves_real_amount_but_blocks_on_missing_vendor_price() -> None:
    """The plan_id resolves to the real, correct amount/currency (19.99 USD)
    — what's missing is only the vendor-side Stripe Price object, which
    requires a real API call to provision (out of scope this wave)."""
    provider = StripeProvider(
        api_key="sk_test", webhook_secret=None, pricing={"focus_monthly_usd": _FOCUS_MONTHLY_USD}
    )
    assert provider._pricing["focus_monthly_usd"].amount == Decimal("19.99")
    assert provider._pricing["focus_monthly_usd"].currency == "USD"
    with pytest.raises(PaymentProviderError) as exc:
        await provider.create_subscription(customer_ref="cus_1", plan_id="focus_monthly_usd")
    assert exc.value.kind == PaymentProviderErrorKind.PERMANENT
    assert "No Stripe price configured yet" in exc.value.message
    assert "focus_monthly_usd" in exc.value.message


async def test_razorpay_create_subscription_rejects_unconfigured_credentials() -> None:
    provider = RazorpayProvider(
        key_id=None,
        key_secret=None,
        webhook_secret=None,
        pricing={"focus_monthly_usd": _FOCUS_MONTHLY_USD},
    )
    with pytest.raises(PaymentProviderError) as exc:
        await provider.create_subscription(customer_ref="cust_1", plan_id="focus_monthly_usd")
    assert exc.value.kind == PaymentProviderErrorKind.PERMANENT
    assert "RAZORPAY_KEY_ID" in exc.value.message


async def test_razorpay_create_subscription_rejects_unknown_plan_id() -> None:
    provider = RazorpayProvider(
        key_id="rzp_id", key_secret="rzp_secret", webhook_secret=None, pricing={}
    )
    with pytest.raises(PaymentProviderError) as exc:
        await provider.create_subscription(customer_ref="cust_1", plan_id="not_a_real_plan")
    assert exc.value.kind == PaymentProviderErrorKind.PERMANENT
    assert "Unknown plan_id" in exc.value.message


async def test_razorpay_create_subscription_resolves_real_amount_but_blocks_on_missing_vendor_plan() -> None:
    provider = RazorpayProvider(
        key_id="rzp_id",
        key_secret="rzp_secret",
        webhook_secret=None,
        pricing={"focus_monthly_usd": _FOCUS_MONTHLY_USD},
    )
    with pytest.raises(PaymentProviderError) as exc:
        await provider.create_subscription(customer_ref="cust_1", plan_id="focus_monthly_usd")
    assert exc.value.kind == PaymentProviderErrorKind.PERMANENT
    assert "No Razorpay plan configured yet" in exc.value.message
    assert "focus_monthly_usd" in exc.value.message


def test_create_subscription_defaults_to_empty_pricing_when_not_provided() -> None:
    """get_stripe_provider/get_razorpay_provider callers who only need
    verify_webhook/cancel_subscription (e.g. the webhook router) never have
    to supply a pricing catalog."""
    stripe = get_stripe_provider(_FakeSettings())
    razorpay = get_razorpay_provider(_FakeSettings())
    assert stripe._pricing == {}
    assert razorpay._pricing == {}
