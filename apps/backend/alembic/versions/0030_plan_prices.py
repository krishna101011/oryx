"""Plan/price catalog — the real, decided ORYX pricing.

Creates `plan_prices`: tier x cadence x currency -> amount, keyed by a
stable internal `plan_id` (e.g. "focus_monthly_usd") that
PaymentProvider.create_subscription now takes instead of a raw vendor price
id (see core/payment_provider.py's PlanPriceRef plumbing, same wave).

18 real rows, no placeholders — Focus/Clarity/Vision x monthly/quarterly/
yearly x USD/INR. Glimpse has no row (free tier, nothing to price).
stripe_price_id/razorpay_plan_id are NULL for every row: populating them
means creating a real Stripe Price / Razorpay Plan object via a live API
call, which is out of scope until checkout actually goes live. Until then,
create_subscription resolves the correct real amount/currency for a given
plan_id but raises PERMANENT for any plan_id whose vendor reference isn't
provisioned yet — the same "real logic, gated on missing config" shape as
the existing missing-API-key guard.

Revision ID: 0030_plan_prices
Revises: 0029_billing_foundation
Create Date: 2026-07-26
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0030_plan_prices"
down_revision = "0029_billing_foundation"
branch_labels = None
depends_on = None

_PLAN_ENUM = postgresql.ENUM(
    "glimpse", "focus", "clarity", "vision", name="workspace_plan", create_type=False
)
_CADENCE_ENUM = postgresql.ENUM(
    "monthly", "quarterly", "yearly", name="billing_cadence", create_type=False
)
_CURRENCY_ENUM = postgresql.ENUM("USD", "INR", name="billing_currency", create_type=False)

# tier -> {cadence: amount} per currency. Exact decided values — no rounding,
# no placeholders.
_USD_PRICES = {
    "focus": {"monthly": "19.99", "quarterly": "53.99", "yearly": "199.99"},
    "clarity": {"monthly": "44.99", "quarterly": "121.99", "yearly": "449.99"},
    "vision": {"monthly": "99.99", "quarterly": "269.99", "yearly": "999.99"},
}
_INR_PRICES = {
    "focus": {"monthly": "999", "quarterly": "2599", "yearly": "9999"},
    "clarity": {"monthly": "2299", "quarterly": "5999", "yearly": "21999"},
    "vision": {"monthly": "4999", "quarterly": "12999", "yearly": "48999"},
}


def _rows() -> list[dict]:
    rows = []
    for currency, table in (("USD", _USD_PRICES), ("INR", _INR_PRICES)):
        for tier, cadences in table.items():
            for cadence, amount in cadences.items():
                rows.append(
                    {
                        "plan_id": f"{tier}_{cadence}_{currency.lower()}",
                        "tier": tier,
                        "cadence": cadence,
                        "currency": currency,
                        "amount": amount,
                        "stripe_price_id": None,
                        "razorpay_plan_id": None,
                    }
                )
    return rows


def upgrade() -> None:
    op.execute("CREATE TYPE billing_cadence AS ENUM ('monthly', 'quarterly', 'yearly')")
    op.execute("CREATE TYPE billing_currency AS ENUM ('USD', 'INR')")
    op.create_table(
        "plan_prices",
        sa.Column("plan_id", sa.Text(), primary_key=True),
        sa.Column("tier", _PLAN_ENUM, nullable=False),
        sa.Column("cadence", _CADENCE_ENUM, nullable=False),
        sa.Column("currency", _CURRENCY_ENUM, nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("stripe_price_id", sa.Text(), nullable=True),
        sa.Column("razorpay_plan_id", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "tier", "cadence", "currency", name="uq_plan_prices_tier_cadence_currency"
        ),
    )

    plan_prices = sa.table(
        "plan_prices",
        sa.column("plan_id", sa.Text()),
        # Bound as the real enum types (not sa.Text()) — asyncpg sends
        # explicit ::VARCHAR casts for plain Text columns, and Postgres has
        # no implicit VARCHAR->enum assignment cast for parameterized
        # INSERT, so a Text-typed bind here fails with "column is of type
        # workspace_plan but expression is of type character varying"
        # (confirmed empirically; same class of issue 0029 hit on UPDATE).
        sa.column("tier", _PLAN_ENUM),
        sa.column("cadence", _CADENCE_ENUM),
        sa.column("currency", _CURRENCY_ENUM),
        sa.column("amount", sa.Numeric(10, 2)),
        sa.column("stripe_price_id", sa.Text()),
        sa.column("razorpay_plan_id", sa.Text()),
    )
    op.bulk_insert(plan_prices, _rows())


def downgrade() -> None:
    op.drop_table("plan_prices")
    op.execute("DROP TYPE IF EXISTS billing_currency")
    op.execute("DROP TYPE IF EXISTS billing_cadence")
