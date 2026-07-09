"""Enable ff_email_delivery.

The email-delivery wave shipped everything the flag stands for: a real
EmailProvider implementation (SendGrid/SMTP behind the EMAIL_PROVIDER switch,
log_only default) wired into NotificationDispatcher as its own decoupled
per-account step with quiet-hours evaluation and per-channel decision rows,
tested end to end (instant alerts only — emailed digests remain out of scope
per the frozen doc §4.2).

Same reasoning standard as 0016 (ff_automation), 0018 (ff_push_delivery) and
0020 (ff_analytics): safe to flip because (a) the flag currently gates NO
client surface — flipping it changes nothing a user can see or break; (b) the
server-side behavior it describes is double-gated by per-account preferences
and by EMAIL_PROVIDER, which defaults to log_only, so no real email leaves any
environment until an operator explicitly configures a provider; (c) every
decision the step takes is recorded in automation_log and rendered by the
already-shipped Automation Hub vocabulary. Worst case is the status quo.

Data-only migration; no schema change.

Revision ID: 0022_email_delivery_flag
Revises: 0021_publication_citations
Create Date: 2026-07-10
"""
from __future__ import annotations

from alembic import op

revision = "0022_email_delivery_flag"
down_revision = "0021_publication_citations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE feature_flags SET default_enabled = true WHERE key = 'ff_email_delivery'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE feature_flags SET default_enabled = false WHERE key = 'ff_email_delivery'"
    )
