"""preferences grows an account-synced theme_mode column (theming Phase A).

The mobile/web client's light/dark switch persists through the existing
/v1/preferences PATCH (the established Preferences convention) rather than a
device-local store, so the choice follows the account across devices.

Existing rows backfill to 'dark' via server_default — dark is the brand
baseline every account has been seeing since Phase 1.

Revision ID: 0025_preferences_theme_mode
Revises: 0024_automation_log_detail
Create Date: 2026-07-16
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0025_preferences_theme_mode"
down_revision = "0024_automation_log_detail"
branch_labels = None
depends_on = None

theme_mode = sa.Enum("dark", "light", name="theme_mode")


def upgrade() -> None:
    theme_mode.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "preferences",
        sa.Column("theme_mode", theme_mode, nullable=False, server_default="dark"),
    )


def downgrade() -> None:
    op.drop_column("preferences", "theme_mode")
    theme_mode.drop(op.get_bind(), checkfirst=True)
