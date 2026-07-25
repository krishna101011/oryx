"""Billing foundation — widen Workspace.plan to the real 4-tier model, add
the Stripe/Razorpay subscription state ledger.

TIER MAPPING (a real product decision made in this migration, not left
implicit): free -> glimpse, pro -> focus, enterprise -> vision. 'clarity' is
a brand-new middle-paid tier; no existing workspace maps onto it, and
nothing is retroactively assigned to it here.

ENUM WIDENING APPROACH: NOT `ALTER TYPE ... ADD VALUE`. This project's
alembic/env.py runs every pending migration inside ONE transaction per
`upgrade` invocation (context.run_migrations() is wrapped in a single
context.begin_transaction(), not one per revision) — so a later statement
using a value `ADD VALUE` just added hits Postgres's "unsafe use of new
value of enum type" error (confirmed empirically while writing this
migration; splitting `ADD VALUE` and its use across two migration files
still fails, because both land in the one transaction alembic opens for the
whole pending batch).

Instead this migration builds a fresh `workspace_plan_new` type with exactly
the 4 real tier labels, casts the column across via `USING` with an explicit
CASE mapping, drops the old type, and renames the new type onto the old
name. Values are usable immediately because they were present at the type's
creation, not added afterward — sidestepping the restriction entirely. As a
side effect this is cleaner than 0014's additive-widen precedent for
activity_type: the retired 'free'/'pro'/'enterprise' labels are dropped
outright (DROP TYPE) rather than surviving forever as unreachable Postgres
labels, because (recon-confirmed) nothing in the codebase reads or writes
`plan` today and every existing row is converted by this same migration.

Also creates the vendor-agnostic subscription state ledger the billing
webhook handlers (services/billing/) write to:
  - payment_provider enum ('stripe' | 'razorpay')
  - subscription_status enum ('pending' | 'active' | 'past_due' | 'canceled')
    — the canonical lifecycle both vendors' webhook events resolve onto
    (services/billing/state.py); PENDING covers AFA-in-progress states
    (Stripe subscription.created pre-first-invoice, Razorpay
    authenticated/pending) that must NEVER promote Workspace.plan.
  - workspace_subscriptions — one row per vendor subscription.
    UNIQUE(provider, provider_subscription_id) is the durable cross-reference
    the webhook handler resolves an inbound event against.

Revision ID: 0029_billing_foundation
Revises: 0028_catalog_the_block_feed
Create Date: 2026-07-25
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0029_billing_foundation"
down_revision = "0028_catalog_the_block_feed"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)

_PLAN_ENUM = postgresql.ENUM(
    "glimpse", "focus", "clarity", "vision", name="workspace_plan", create_type=False
)
_PROVIDER_ENUM = postgresql.ENUM(
    "stripe", "razorpay", name="payment_provider", create_type=False
)
_STATUS_ENUM = postgresql.ENUM(
    "pending", "active", "past_due", "canceled", name="subscription_status", create_type=False
)


def upgrade() -> None:
    # 1 — swap workspace_plan for a freshly-created type with exactly the 4
    # real tier labels (see module docstring for why not ADD VALUE).
    op.execute(
        "CREATE TYPE workspace_plan_new AS ENUM "
        "('glimpse', 'focus', 'clarity', 'vision')"
    )
    op.execute("ALTER TABLE workspaces ALTER COLUMN plan DROP DEFAULT")
    op.execute(
        "ALTER TABLE workspaces ALTER COLUMN plan TYPE workspace_plan_new USING ("
        "CASE plan::text "
        "WHEN 'free' THEN 'glimpse' "
        "WHEN 'pro' THEN 'focus' "
        "WHEN 'enterprise' THEN 'vision' "
        "ELSE plan::text END"
        ")::workspace_plan_new"
    )
    op.execute(
        "ALTER TABLE workspaces ALTER COLUMN plan SET DEFAULT 'glimpse'::workspace_plan_new"
    )
    op.execute("DROP TYPE workspace_plan")
    op.execute("ALTER TYPE workspace_plan_new RENAME TO workspace_plan")

    # 2 — payment_provider + subscription_status enums, workspace_subscriptions.
    op.execute("CREATE TYPE payment_provider AS ENUM ('stripe', 'razorpay')")
    op.execute(
        "CREATE TYPE subscription_status AS ENUM "
        "('pending', 'active', 'past_due', 'canceled')"
    )
    op.create_table(
        "workspace_subscriptions",
        sa.Column(
            "id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "workspace_id",
            _UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", _PROVIDER_ENUM, nullable=False),
        sa.Column("provider_subscription_id", sa.Text(), nullable=False),
        # Nullable: unknown until the (not-yet-built) checkout flow stashes
        # the target tier in the vendor's own metadata/notes at creation
        # time. See core/models.py's WorkspaceSubscription docstring.
        sa.Column("plan", _PLAN_ENUM, nullable=True),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column(
            "status", _STATUS_ENUM, nullable=False, server_default="pending"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "provider",
            "provider_subscription_id",
            name="uq_workspace_subscriptions_provider_ref",
        ),
    )
    op.create_index(
        "ix_workspace_subscriptions_workspace",
        "workspace_subscriptions",
        ["workspace_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_workspace_subscriptions_workspace", table_name="workspace_subscriptions"
    )
    op.drop_table("workspace_subscriptions")
    op.execute("DROP TYPE IF EXISTS subscription_status")
    op.execute("DROP TYPE IF EXISTS payment_provider")

    # Reverse the type swap the same way it was made: a fresh type with the
    # old labels, cast across via USING, then rename onto workspace_plan.
    # 'clarity' has no pre-migration equivalent — best-effort maps to 'pro',
    # the closest available meaning. Lossy by necessity.
    op.execute("CREATE TYPE workspace_plan_old AS ENUM ('free', 'pro', 'enterprise')")
    op.execute("ALTER TABLE workspaces ALTER COLUMN plan DROP DEFAULT")
    op.execute(
        "ALTER TABLE workspaces ALTER COLUMN plan TYPE workspace_plan_old USING ("
        "CASE plan::text "
        "WHEN 'glimpse' THEN 'free' "
        "WHEN 'focus' THEN 'pro' "
        "WHEN 'clarity' THEN 'pro' "
        "WHEN 'vision' THEN 'enterprise' "
        "ELSE plan::text END"
        ")::workspace_plan_old"
    )
    op.execute(
        "ALTER TABLE workspaces ALTER COLUMN plan SET DEFAULT 'free'::workspace_plan_old"
    )
    op.execute("DROP TYPE workspace_plan")
    op.execute("ALTER TYPE workspace_plan_old RENAME TO workspace_plan")
