"""Phase 6 Wave B — digest_runs (the DigestWorker's idempotency record).

profiles.timezone ALREADY EXISTS (0001_phase2_baseline.py line 124: text,
NOT NULL, server_default 'UTC') — Wave B reuses it, no column is added here.

CREATEs digest_runs — one row per SENT digest window, mirroring
automation_log's idempotency approach from Wave A:
UNIQUE(account_id, activity_type, frequency, window_start) makes a second
tick inside the same window a safe no-op, the same principle as
uq_automation_log_account_event in 0014. `activity_type` here is the single
content category the digest bundled (security/system/verification/publishing);
the daily_digest/weekly_digest bundle-row marker lives on the activity_inbox
row the run produced, per the Rev 2 §3.1 usage convention.

NO additional index (the 0014 justify-or-don't rule): the worker issues only
two queries against this table — latest run for (account_id, activity_type,
frequency), and an exact-key existence check on (account_id, activity_type,
frequency, window_start). Both are served by the unique constraint's backing
btree index (its first three columns are a prefix of it), so a separate index
would duplicate it. Nothing to EXPLAIN-justify because nothing extra is added.

Revision ID: 0015_phase6_wave_b
Revises: 0014_phase6_wave_a
Create Date: 2026-07-07
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0015_phase6_wave_b"
down_revision = "0014_phase6_wave_a"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)

# Both enums already exist (activity_type from 0001 widened in 0014,
# notification_frequency from 0001) — reference them, never re-create.
_ACTIVITY_TYPE = postgresql.ENUM(
    "security", "system", "instant_alert", "daily_digest", "weekly_digest",
    "verification", "publishing",
    name="activity_type", create_type=False,
)
_FREQUENCY = postgresql.ENUM(
    "off", "instant", "daily", "weekly",
    name="notification_frequency", create_type=False,
)


def upgrade() -> None:
    op.create_table(
        "digest_runs",
        sa.Column(
            "id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "account_id",
            _UUID,
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("activity_type", _ACTIVITY_TYPE, nullable=False),
        sa.Column("frequency", _FREQUENCY, nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        # One sent digest per (account, category, cadence, window) — a double
        # tick inside the same window is a safe no-op (same principle as
        # automation_log's uq_automation_log_account_event).
        sa.UniqueConstraint(
            "account_id",
            "activity_type",
            "frequency",
            "window_start",
            name="uq_digest_runs_window",
        ),
    )


def downgrade() -> None:
    op.drop_table("digest_runs")
