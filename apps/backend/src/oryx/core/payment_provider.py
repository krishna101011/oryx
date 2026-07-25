"""Pluggable payment-provider abstraction. Mirrors core/ai_provider.py's
Protocol + factory shape exactly: one narrow interface, vendor errors
collapsed onto a shared taxonomy before they cross the boundary, a factory
that picks the concrete implementation so callers never branch on vendor.

Currency-routing rationale (recon, not an assumption): Stripe India accounts
are invite-only and export-oriented, cannot receive INR payouts for a
non-India-registered business, and the RBI e-mandate framework (2026) makes
Razorpay — built directly against those rules — the practical rail for
Indian-domestic recurring billing. INR routes to Razorpay; every other
currency routes to Stripe.

FOUNDATION WAVE: create_subscription/cancel_subscription are real HTTP calls
shaped exactly like each vendor's REST API, but no live credential is
configured by default (Settings.stripe_api_key / razorpay_key_id+key_secret
are None) — both providers raise PaymentProviderError(PERMANENT) pre-flight,
exactly like OpenAICompatProvider's missing-config guard in ai_provider.py.
verify_webhook has NO such gate: signature verification is real, live, and
independently testable against a synthetic secret with no vendor credentials
required — it must run before any other webhook handling (non-negotiable;
see services/billing/webhook_router.py).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol, runtime_checkable

import httpx

_STRIPE_API_URL = "https://api.stripe.com/v1"
_RAZORPAY_API_URL = "https://api.razorpay.com/v1"

# Stripe's own tolerance for clock drift between the signed timestamp and now.
STRIPE_SIGNATURE_TOLERANCE_SECONDS = 300


class PaymentProviderErrorKind(str, Enum):
    TRANSIENT = "transient"                  # 5xx, network blip, timeout
    RATE_LIMITED = "rate_limited"             # 429
    AUTH = "auth"                              # API key/credential rejected
    DECLINED = "declined"                      # card/mandate declined by the bank
    PERMANENT = "permanent"                    # bad request, missing config
    SIGNATURE_INVALID = "signature_invalid"    # webhook signature failed verification
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class PaymentProviderError(Exception):
    kind: PaymentProviderErrorKind
    message: str
    provider: str
    retry_after_seconds: int | None = None

    def __str__(self) -> str:  # pragma: no cover — trivial
        return f"{self.provider}/{self.kind.value}: {self.message}"


@dataclass(frozen=True)
class SubscriptionHandle:
    """Returned by create_subscription. provider_subscription_id is the
    vendor's own id — the durable cross-reference stored on
    workspace_subscriptions.provider_subscription_id."""

    provider_subscription_id: str
    status: str
    raw: dict[str, Any]


@dataclass(frozen=True)
class WebhookEvent:
    """Returned by verify_webhook once the signature has checked out.

    event_type is the vendor's own event name (e.g.
    "customer.subscription.updated" or "subscription.charged") — the caller
    maps it onto the shared SubscriptionStatus machine (services/billing/state.py).

    workspace_ref/plan_ref are read from the vendor's own metadata/notes
    field on the subscription object — the (not-yet-built) checkout flow is
    expected to stash both there at creation time. Either may be None on a
    real payload until that flow exists; callers must handle that, never
    guess a workspace or tier."""

    event_type: str
    provider_subscription_id: str | None
    workspace_ref: str | None
    plan_ref: str | None
    raw: dict[str, Any]


@runtime_checkable
class PaymentProvider(Protocol):
    name: str

    async def create_subscription(
        self, *, customer_ref: str, plan_ref: str
    ) -> SubscriptionHandle: ...

    def verify_webhook(
        self, *, headers: Mapping[str, str], body: bytes
    ) -> WebhookEvent:
        """Raises PaymentProviderError(SIGNATURE_INVALID) on any failure.
        Synchronous and side-effect free — pure signature math, no network
        call — so it can and must run before anything else touches the
        payload."""
        ...

    async def cancel_subscription(self, *, provider_subscription_id: str) -> None: ...


def _lower_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {k.lower(): v for k, v in headers.items()}


class StripeProvider:
    """Direct Stripe REST API. Vendor errors map onto PaymentProviderError so
    downstream retry/dead-letter handling applies unchanged."""

    name = "stripe"

    def __init__(
        self,
        api_key: str | None,
        webhook_secret: str | None,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._webhook_secret = webhook_secret
        self._timeout = timeout

    async def create_subscription(
        self, *, customer_ref: str, plan_ref: str
    ) -> SubscriptionHandle:
        if not self._api_key:
            raise PaymentProviderError(
                kind=PaymentProviderErrorKind.PERMANENT,
                message="STRIPE_API_KEY is not configured",
                provider=self.name,
            )
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{_STRIPE_API_URL}/subscriptions",
                    headers={"authorization": f"Bearer {self._api_key}"},
                    data={"customer": customer_ref, "items[0][price]": plan_ref},
                )
        except httpx.HTTPError as exc:
            raise PaymentProviderError(
                kind=PaymentProviderErrorKind.TRANSIENT,
                message=f"Stripe unreachable: {exc}",
                provider=self.name,
            ) from exc
        self._raise_for_status(resp)
        data: dict[str, Any] = resp.json()
        return SubscriptionHandle(
            provider_subscription_id=data["id"],
            status=data.get("status", "unknown"),
            raw=data,
        )

    def verify_webhook(self, *, headers: Mapping[str, str], body: bytes) -> WebhookEvent:
        if not self._webhook_secret:
            raise PaymentProviderError(
                kind=PaymentProviderErrorKind.PERMANENT,
                message="STRIPE_WEBHOOK_SECRET is not configured",
                provider=self.name,
            )
        header = _lower_headers(headers).get("stripe-signature")
        if not header:
            raise PaymentProviderError(
                kind=PaymentProviderErrorKind.SIGNATURE_INVALID,
                message="Missing Stripe-Signature header",
                provider=self.name,
            )
        parts: dict[str, list[str]] = {}
        for chunk in header.split(","):
            if "=" not in chunk:
                continue
            key, _, value = chunk.partition("=")
            parts.setdefault(key.strip(), []).append(value.strip())
        timestamps = parts.get("t")
        signatures = parts.get("v1")
        if not timestamps or not signatures:
            raise PaymentProviderError(
                kind=PaymentProviderErrorKind.SIGNATURE_INVALID,
                message="Malformed Stripe-Signature header",
                provider=self.name,
            )
        try:
            ts = int(timestamps[0])
        except ValueError as exc:
            raise PaymentProviderError(
                kind=PaymentProviderErrorKind.SIGNATURE_INVALID,
                message="Non-integer timestamp in Stripe-Signature",
                provider=self.name,
            ) from exc
        if abs(int(time.time()) - ts) > STRIPE_SIGNATURE_TOLERANCE_SECONDS:
            raise PaymentProviderError(
                kind=PaymentProviderErrorKind.SIGNATURE_INVALID,
                message="Stripe-Signature timestamp outside tolerance",
                provider=self.name,
            )
        signed_payload = f"{ts}.".encode("ascii") + body
        expected = hmac.new(
            self._webhook_secret.encode("utf-8"), signed_payload, hashlib.sha256
        ).hexdigest()
        if not any(hmac.compare_digest(expected, sig) for sig in signatures):
            raise PaymentProviderError(
                kind=PaymentProviderErrorKind.SIGNATURE_INVALID,
                message="Stripe signature does not match",
                provider=self.name,
            )
        try:
            payload: dict[str, Any] = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PaymentProviderError(
                kind=PaymentProviderErrorKind.SIGNATURE_INVALID,
                message="Stripe payload is not valid JSON",
                provider=self.name,
            ) from exc
        data_object = ((payload.get("data") or {}).get("object")) or {}
        metadata = data_object.get("metadata") or {} if isinstance(data_object, dict) else {}
        return WebhookEvent(
            event_type=payload.get("type", "unknown"),
            provider_subscription_id=data_object.get("id") if isinstance(data_object, dict) else None,
            workspace_ref=metadata.get("workspace_id"),
            plan_ref=metadata.get("workspace_plan"),
            raw=payload,
        )

    async def cancel_subscription(self, *, provider_subscription_id: str) -> None:
        if not self._api_key:
            raise PaymentProviderError(
                kind=PaymentProviderErrorKind.PERMANENT,
                message="STRIPE_API_KEY is not configured",
                provider=self.name,
            )
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.delete(
                    f"{_STRIPE_API_URL}/subscriptions/{provider_subscription_id}",
                    headers={"authorization": f"Bearer {self._api_key}"},
                )
        except httpx.HTTPError as exc:
            raise PaymentProviderError(
                kind=PaymentProviderErrorKind.TRANSIENT,
                message=f"Stripe unreachable: {exc}",
                provider=self.name,
            ) from exc
        self._raise_for_status(resp)

    def _raise_for_status(self, resp: httpx.Response) -> None:
        if resp.status_code == 401:
            raise PaymentProviderError(
                kind=PaymentProviderErrorKind.AUTH,
                message="Stripe API key rejected",
                provider=self.name,
            )
        if resp.status_code == 402:
            raise PaymentProviderError(
                kind=PaymentProviderErrorKind.DECLINED,
                message="Stripe payment declined",
                provider=self.name,
            )
        if resp.status_code == 429:
            retry_after = resp.headers.get("retry-after")
            raise PaymentProviderError(
                kind=PaymentProviderErrorKind.RATE_LIMITED,
                message="Stripe rate limit",
                provider=self.name,
                retry_after_seconds=int(retry_after) if retry_after else None,
            )
        if resp.status_code >= 500:
            raise PaymentProviderError(
                kind=PaymentProviderErrorKind.TRANSIENT,
                message=f"Stripe API {resp.status_code}",
                provider=self.name,
            )
        if resp.status_code >= 400:
            raise PaymentProviderError(
                kind=PaymentProviderErrorKind.PERMANENT,
                message=f"Stripe API {resp.status_code}: {resp.text[:200]}",
                provider=self.name,
            )


class RazorpayProvider:
    """Direct Razorpay REST API (Subscriptions). Vendor errors map onto
    PaymentProviderError with the same status->kind scheme as StripeProvider."""

    name = "razorpay"

    def __init__(
        self,
        key_id: str | None,
        key_secret: str | None,
        webhook_secret: str | None,
        timeout: float = 30.0,
    ) -> None:
        self._key_id = key_id
        self._key_secret = key_secret
        self._webhook_secret = webhook_secret
        self._timeout = timeout

    async def create_subscription(
        self, *, customer_ref: str, plan_ref: str
    ) -> SubscriptionHandle:
        if not (self._key_id and self._key_secret):
            raise PaymentProviderError(
                kind=PaymentProviderErrorKind.PERMANENT,
                message="RAZORPAY_KEY_ID/RAZORPAY_KEY_SECRET are not configured",
                provider=self.name,
            )
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, auth=(self._key_id, self._key_secret)
            ) as client:
                resp = await client.post(
                    f"{_RAZORPAY_API_URL}/subscriptions",
                    json={
                        "plan_id": plan_ref,
                        "customer_notify": 0,
                        "total_count": 120,
                        "notes": {"customer_ref": customer_ref},
                    },
                )
        except httpx.HTTPError as exc:
            raise PaymentProviderError(
                kind=PaymentProviderErrorKind.TRANSIENT,
                message=f"Razorpay unreachable: {exc}",
                provider=self.name,
            ) from exc
        self._raise_for_status(resp)
        data: dict[str, Any] = resp.json()
        return SubscriptionHandle(
            provider_subscription_id=data["id"],
            status=data.get("status", "unknown"),
            raw=data,
        )

    def verify_webhook(self, *, headers: Mapping[str, str], body: bytes) -> WebhookEvent:
        if not self._webhook_secret:
            raise PaymentProviderError(
                kind=PaymentProviderErrorKind.PERMANENT,
                message="RAZORPAY_WEBHOOK_SECRET is not configured",
                provider=self.name,
            )
        presented = _lower_headers(headers).get("x-razorpay-signature")
        if not presented:
            raise PaymentProviderError(
                kind=PaymentProviderErrorKind.SIGNATURE_INVALID,
                message="Missing X-Razorpay-Signature header",
                provider=self.name,
            )
        expected = hmac.new(
            self._webhook_secret.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, presented.strip()):
            raise PaymentProviderError(
                kind=PaymentProviderErrorKind.SIGNATURE_INVALID,
                message="Razorpay signature does not match",
                provider=self.name,
            )
        try:
            payload: dict[str, Any] = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PaymentProviderError(
                kind=PaymentProviderErrorKind.SIGNATURE_INVALID,
                message="Razorpay payload is not valid JSON",
                provider=self.name,
            ) from exc
        entity = (((payload.get("payload") or {}).get("subscription") or {}).get("entity")) or {}
        notes = entity.get("notes") or {} if isinstance(entity, dict) else {}
        return WebhookEvent(
            event_type=payload.get("event", "unknown"),
            provider_subscription_id=entity.get("id") if isinstance(entity, dict) else None,
            workspace_ref=notes.get("workspace_id") if isinstance(notes, dict) else None,
            plan_ref=notes.get("workspace_plan") if isinstance(notes, dict) else None,
            raw=payload,
        )

    async def cancel_subscription(self, *, provider_subscription_id: str) -> None:
        if not (self._key_id and self._key_secret):
            raise PaymentProviderError(
                kind=PaymentProviderErrorKind.PERMANENT,
                message="RAZORPAY_KEY_ID/RAZORPAY_KEY_SECRET are not configured",
                provider=self.name,
            )
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, auth=(self._key_id, self._key_secret)
            ) as client:
                resp = await client.post(
                    f"{_RAZORPAY_API_URL}/subscriptions/{provider_subscription_id}/cancel",
                    json={"cancel_at_cycle_end": 0},
                )
        except httpx.HTTPError as exc:
            raise PaymentProviderError(
                kind=PaymentProviderErrorKind.TRANSIENT,
                message=f"Razorpay unreachable: {exc}",
                provider=self.name,
            ) from exc
        self._raise_for_status(resp)

    def _raise_for_status(self, resp: httpx.Response) -> None:
        if resp.status_code == 401:
            raise PaymentProviderError(
                kind=PaymentProviderErrorKind.AUTH,
                message="Razorpay credentials rejected",
                provider=self.name,
            )
        if resp.status_code == 429:
            raise PaymentProviderError(
                kind=PaymentProviderErrorKind.RATE_LIMITED,
                message="Razorpay rate limit",
                provider=self.name,
            )
        if resp.status_code >= 500:
            raise PaymentProviderError(
                kind=PaymentProviderErrorKind.TRANSIENT,
                message=f"Razorpay API {resp.status_code}",
                provider=self.name,
            )
        if resp.status_code >= 400:
            raise PaymentProviderError(
                kind=PaymentProviderErrorKind.PERMANENT,
                message=f"Razorpay API {resp.status_code}: {resp.text[:200]}",
                provider=self.name,
            )


def get_stripe_provider(settings) -> StripeProvider:
    return StripeProvider(
        api_key=getattr(settings, "stripe_api_key", None),
        webhook_secret=getattr(settings, "stripe_webhook_secret", None),
    )


def get_razorpay_provider(settings) -> RazorpayProvider:
    return RazorpayProvider(
        key_id=getattr(settings, "razorpay_key_id", None),
        key_secret=getattr(settings, "razorpay_key_secret", None),
        webhook_secret=getattr(settings, "razorpay_webhook_secret", None),
    )


def get_payment_provider(settings, *, currency: str) -> PaymentProvider:
    """Factory keyed on workspace currency. currency="INR" -> RazorpayProvider
    (India's e-mandate-aligned recurring rail); everything else -> StripeProvider.
    See module docstring for the routing rationale.

    Used when CREATING a subscription. The webhook router does NOT use this —
    the endpoint path (/billing/webhooks/stripe vs /razorpay) already
    determines the vendor, so it calls get_stripe_provider/get_razorpay_provider
    directly.
    """
    if currency.upper() == "INR":
        return get_razorpay_provider(settings)
    return get_stripe_provider(settings)
