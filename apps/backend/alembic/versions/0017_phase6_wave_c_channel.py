"""Phase 6 Wave C — automation_log grows a channel discriminator.

Wave A keyed dispatcher idempotency on UNIQUE(account_id, triggered_by_event_id)
— one decision per (account, event). The frozen §3.3 action vocabulary, however,
includes push_sent/push_failed: the SAME (account, event) legitimately gets a
second decision row once Wave C delivers on the push channel. So the decision
key becomes per-CHANNEL:

  1. add `channel` (the EXISTING alert_channel enum already used by
     alert_preferences — 'in_app' | 'push', extensible to 'email' later);
  2. backfill every existing row to 'in_app' (all pre-Wave-C rows are in_app
     dispatch decisions by construction);
  3. drop the server_default afterwards so every future insert must say which
     channel it is deciding for — no silent fallback;
  4. replace the unique constraint with
     UNIQUE(account_id, triggered_by_event_id, channel): still exactly one
     decision per (account, event) per channel, still the at-least-once
     redelivery backstop.

Revision ID: 0017_phase6_wave_c_channel
Revises: 0016_phase6_wave_b_ui
Create Date: 2026-07-07
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0017_phase6_wave_c_channel"
down_revision = "0016_phase6_wave_b_ui"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Adding with a server_default backfills existing rows to 'in_app' in the
    # same statement (PostgreSQL fills the column on ADD COLUMN ... DEFAULT).
    op.add_column(
        "automation_log",
        sa.Column(
            "channel",
            sa.Enum("in_app", "push", "email", name="alert_channel", create_type=False),
            nullable=False,
            server_default="in_app",
        ),
    )
    # Explicitness from here on: writers must pass a channel; an insert without
    # one is an error, not a silent 'in_app'.
    op.alter_column("automation_log", "channel", server_default=None)

    op.drop_constraint(
        "uq_automation_log_account_event", "automation_log", type_="unique"
    )
    op.create_unique_constraint(
        "uq_automation_log_account_event_channel",
        "automation_log",
        ["account_id", "triggered_by_event_id", "channel"],
    )


def downgrade() -> None:
    # Push-channel rows cannot survive the narrower Wave A key; drop them
    # before restoring it.
    op.execute("DELETE FROM automation_log WHERE channel != 'in_app'")
    op.drop_constraint(
        "uq_automation_log_account_event_channel", "automation_log", type_="unique"
    )
    op.create_unique_constraint(
        "uq_automation_log_account_event",
        "automation_log",
        ["account_id", "triggered_by_event_id"],
    )
    op.drop_column("automation_log", "channel")
