"""plan_prices catalog (migration 0030): every one of the 18 real price
points is independently retrievable with its exact decided amount, and
Glimpse (the free tier) has no paid row."""
from __future__ import annotations

from decimal import Decimal

import pytest

pytestmark = pytest.mark.requires_db

# (tier, cadence, currency) -> exact decided amount. The 9 USD + 9 INR
# points from the pricing decision — no placeholders, no rounding.
EXPECTED_PRICES: dict[tuple[str, str, str], Decimal] = {
    ("focus", "monthly", "USD"): Decimal("19.99"),
    ("focus", "quarterly", "USD"): Decimal("53.99"),
    ("focus", "yearly", "USD"): Decimal("199.99"),
    ("clarity", "monthly", "USD"): Decimal("44.99"),
    ("clarity", "quarterly", "USD"): Decimal("121.99"),
    ("clarity", "yearly", "USD"): Decimal("449.99"),
    ("vision", "monthly", "USD"): Decimal("99.99"),
    ("vision", "quarterly", "USD"): Decimal("269.99"),
    ("vision", "yearly", "USD"): Decimal("999.99"),
    ("focus", "monthly", "INR"): Decimal("999"),
    ("focus", "quarterly", "INR"): Decimal("2599"),
    ("focus", "yearly", "INR"): Decimal("9999"),
    ("clarity", "monthly", "INR"): Decimal("2299"),
    ("clarity", "quarterly", "INR"): Decimal("5999"),
    ("clarity", "yearly", "INR"): Decimal("21999"),
    ("vision", "monthly", "INR"): Decimal("4999"),
    ("vision", "quarterly", "INR"): Decimal("12999"),
    ("vision", "yearly", "INR"): Decimal("48999"),
}


def _plan_id(tier: str, cadence: str, currency: str) -> str:
    return f"{tier}_{cadence}_{currency.lower()}"


@pytest.mark.parametrize(
    "tier,cadence,currency,expected", [(t, c, cur, amt) for (t, c, cur), amt in EXPECTED_PRICES.items()]
)
async def test_price_point_is_retrievable_with_exact_amount(
    sm, tier: str, cadence: str, currency: str, expected: Decimal
) -> None:
    from oryx.services.billing.repository import PlanPriceRepository

    async with sm() as session:
        repo = PlanPriceRepository(session)
        ref = await repo.get(_plan_id(tier, cadence, currency))

    assert ref is not None
    assert ref.tier == tier
    assert ref.cadence == cadence
    assert ref.currency == currency
    assert ref.amount == expected


async def test_catalog_has_exactly_18_rows(sm) -> None:
    from oryx.services.billing.repository import PlanPriceRepository

    async with sm() as session:
        repo = PlanPriceRepository(session)
        catalog = await repo.load_all()

    assert len(catalog) == 18
    assert set(catalog.keys()) == {
        _plan_id(t, c, cur) for (t, c, cur) in EXPECTED_PRICES
    }


async def test_glimpse_has_no_paid_price_row(sm) -> None:
    from oryx.services.billing.repository import PlanPriceRepository

    async with sm() as session:
        repo = PlanPriceRepository(session)
        catalog = await repo.load_all()

    assert all(ref.tier != "glimpse" for ref in catalog.values())
    for cadence in ("monthly", "quarterly", "yearly"):
        for currency in ("USD", "INR"):
            async with sm() as session:
                repo = PlanPriceRepository(session)
                ref = await repo.get(_plan_id("glimpse", cadence, currency))
            assert ref is None


async def test_vendor_reference_columns_are_unprovisioned(sm) -> None:
    """Foundation-wave scope check: no plan_id has a real Stripe/Razorpay
    reference yet — provisioning those requires a live vendor API call,
    explicitly out of scope until checkout goes live."""
    from oryx.services.billing.repository import PlanPriceRepository

    async with sm() as session:
        repo = PlanPriceRepository(session)
        catalog = await repo.load_all()

    assert len(catalog) == 18
    for ref in catalog.values():
        assert ref.stripe_price_id is None
        assert ref.razorpay_plan_id is None
