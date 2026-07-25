"""Canonical subscription lifecycle — maps each vendor's own webhook event
vocabulary onto one shared SubscriptionStatus so BillingService never
branches on which provider fired. Mirrors the same "collapse vendor variance
before it crosses the boundary" idea as intake/providers/errors.py's
ProviderErrorKind.

PENDING covers every state where a customer-authentication (AFA) step is
still outstanding or a charge attempt hasn't resolved yet — Stripe's bare
subscription.created before its first paid invoice; Razorpay's
authenticated/pending. Workspace.plan must NEVER update on PENDING, and an
unrecognized event name resolves to PENDING too (the safe default — an
event we don't understand yet must not promote a workspace)."""
from __future__ import annotations

from enum import Enum
from typing import Any


class SubscriptionStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"


# Stripe: keyed on the webhook event's `type`. `customer.subscription.updated`
# is resolved separately below — its true status rides in
# `data.object.status`, not the event name.
_STRIPE_STATUS_BY_EVENT: dict[str, SubscriptionStatus] = {
    "customer.subscription.created": SubscriptionStatus.PENDING,
    "invoice.paid": SubscriptionStatus.ACTIVE,
    "invoice.payment_failed": SubscriptionStatus.PAST_DUE,
    "customer.subscription.deleted": SubscriptionStatus.CANCELED,
}

# Stripe's own `subscription.status` field (present on
# customer.subscription.updated's data.object) mapped onto the shared enum.
_STRIPE_STATUS_BY_OBJECT_STATUS: dict[str, SubscriptionStatus] = {
    "trialing": SubscriptionStatus.PENDING,
    "incomplete": SubscriptionStatus.PENDING,
    "incomplete_expired": SubscriptionStatus.CANCELED,
    "active": SubscriptionStatus.ACTIVE,
    "past_due": SubscriptionStatus.PAST_DUE,
    "unpaid": SubscriptionStatus.PAST_DUE,
    "canceled": SubscriptionStatus.CANCELED,
}

_RAZORPAY_STATUS_BY_EVENT: dict[str, SubscriptionStatus] = {
    "subscription.authenticated": SubscriptionStatus.PENDING,
    "subscription.pending": SubscriptionStatus.PENDING,
    "subscription.activated": SubscriptionStatus.ACTIVE,
    "subscription.charged": SubscriptionStatus.ACTIVE,
    "subscription.resumed": SubscriptionStatus.ACTIVE,
    "subscription.halted": SubscriptionStatus.PAST_DUE,
    "subscription.paused": SubscriptionStatus.PAST_DUE,
    "subscription.cancelled": SubscriptionStatus.CANCELED,
    "subscription.completed": SubscriptionStatus.CANCELED,
}


def resolve_status(*, provider: str, event_type: str, raw: dict[str, Any]) -> SubscriptionStatus:
    """Pure function: vendor event -> canonical SubscriptionStatus. Unknown
    provider/event_type combinations resolve to PENDING."""
    if provider == "stripe":
        if event_type == "customer.subscription.updated":
            data_object = (raw.get("data") or {}).get("object") or {}
            object_status = (
                data_object.get("status") if isinstance(data_object, dict) else None
            )
            return _STRIPE_STATUS_BY_OBJECT_STATUS.get(
                object_status, SubscriptionStatus.PENDING
            )
        return _STRIPE_STATUS_BY_EVENT.get(event_type, SubscriptionStatus.PENDING)
    if provider == "razorpay":
        return _RAZORPAY_STATUS_BY_EVENT.get(event_type, SubscriptionStatus.PENDING)
    return SubscriptionStatus.PENDING
