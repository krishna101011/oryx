"""automation_log grows a nullable free-text `detail` column (2026-07-12).

The dispatcher has always COMPUTED a real failure reason for push/email
failures ("no_registered_device", "fcm: <provider error>", ...) but only wrote
it to the operational log — the automation_log row said 'push_failed' with
nothing behind it, so the Automation Hub could not answer "why did it fail?".
This column persists that reason on the decision row itself.

Nullable on purpose:
  - success/suppression rows carry no reason (NULL is correct, not missing);
  - every pre-existing row predates reason capture — the UI states that
    honestly rather than inventing one, so NO backfill.

Revision ID: 0024_automation_log_detail
Revises: 0023_intake_rss_flag
Create Date: 2026-07-12
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0024_automation_log_detail"
down_revision = "0023_intake_rss_flag"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("automation_log", sa.Column("detail", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("automation_log", "detail")
