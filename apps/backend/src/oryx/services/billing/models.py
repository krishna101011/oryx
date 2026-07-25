"""Billing domain entities — frozen dataclasses, no SQLAlchemy.

The repository converts between ORM rows (core/models.py's PlanPrice) and
these. PlanPriceRef is also the type PaymentProvider implementations
(core/payment_provider.py) resolve plan_id against — core/ imports this
dataclass but never queries the DB directly, so StripeProvider/
RazorpayProvider stay framework-light like AnthropicProvider/OllamaProvider.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

BILLING_TIERS = ("focus", "clarity", "vision")  # glimpse is free — no price row
BILLING_CADENCES = ("monthly", "quarterly", "yearly")
BILLING_CURRENCIES = ("USD", "INR")


@dataclass(frozen=True)
class PlanPriceRef:
    """One (tier, cadence, currency) price point — the real decided amount,
    plus whichever vendor-specific reference (if any) has been provisioned
    for it. stripe_price_id/razorpay_plan_id are None until a future wave
    creates the corresponding vendor Price/Plan object via a real API call —
    that provisioning step is explicitly out of scope for the billing
    foundation wave that introduced this table."""

    plan_id: str
    tier: str
    cadence: str
    currency: str
    amount: Decimal
    stripe_price_id: str | None
    razorpay_plan_id: str | None
