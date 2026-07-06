"""Phase 6 Wave A — notification dispatch foundations.

REUSES the Phase 2 activity infrastructure rather than building parallel
tables (frozen architecture docs/PHASE_6_ARCHITECTURE.md Rev 2, commit c8b64a0):

ALTERs activity_inbox (the existing feed) — it gains the columns a dispatched
notification needs and the feed never had:
  + severity   activity_severity ('info'|'warning'|'error'), NOT NULL DEFAULT 'info'
  + source_event_type  text NULL — the outbox event name that produced the row
  + source_event_id    uuid NULL — traceable back to outbox_events

Widens the existing activity_type enum additively with the two content
categories Phase 6 dispatches into:
  + 'verification'   (Verify/Analyze surface)
  + 'publishing'     (Create/Publish surface)
The pre-existing 'security'/'system' values are untouched; the reserved
cadence-label values ('instant_alert'/'daily_digest'/'weekly_digest') are NOT
written to alert_preferences by Phase 6 — they stay reserved for activity_inbox
bundle rows in Wave B's DigestWorker.

Adds ix_activity_account_unread (account_id, read_at, created_at DESC) — an
EXPLAIN-justified index for the hot unread-count query. On the pre-existing
(account_id, created_at) index that query bitmap-scans ALL of an account's rows
then filters read_at (cost ~191, work grows with total history); the new index
serves it as an Index Only Scan (Heap Fetches: 0, cost ~4.5, work grows only
with unread count). The existing ix_activity_account_time is KEPT — it still
serves the feed-page (ORDER BY created_at DESC) query best; the new index does
not replace it.

CREATEs automation_log — the one genuinely new table. Every dispatcher decision
(a notification created OR suppressed by preference) writes exactly one row, so
the Automation Hub (Wave C) can answer both "why did I get this" and "why did I
NOT". UNIQUE(account_id, triggered_by_event_id) is the dispatcher's idempotency
key under the outbox's at-least-once delivery contract.

Revision ID: 0014_phase6_wave_a
Revises: 0013_phase5_wave_e
Create Date: 2026-06-30
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0014_phase6_wave_a"
down_revision = "0013_phase5_wave_e"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)

_SEVERITY_ENUM = postgresql.ENUM(
    "info", "warning", "error", name="activity_severity", create_type=False
)


def upgrade() -> None:
    # 1 — new severity enum + the three new activity_inbox columns.
    op.execute("CREATE TYPE activity_severity AS ENUM ('info', 'warning', 'error')")
    op.add_column(
        "activity_inbox",
        sa.Column(
            "severity", _SEVERITY_ENUM, nullable=False, server_default="info"
        ),
    )
    op.add_column(
        "activity_inbox", sa.Column("source_event_type", sa.Text(), nullable=True)
    )
    op.add_column(
        "activity_inbox", sa.Column("source_event_id", _UUID, nullable=True)
    )

    # 2 — widen activity_type additively. ADD VALUE is transaction-safe on PG12+
    # as long as the new value is not USED in the same transaction (it isn't —
    # no rows are written here). IF NOT EXISTS keeps re-runs safe.
    op.execute("ALTER TYPE activity_type ADD VALUE IF NOT EXISTS 'verification'")
    op.execute("ALTER TYPE activity_type ADD VALUE IF NOT EXISTS 'publishing'")

    # 3 — EXPLAIN-justified unread-count index (added, NOT replacing the existing
    # feed index). See module docstring for the EXPLAIN evidence.
    op.create_index(
        "ix_activity_account_unread",
        "activity_inbox",
        ["account_id", "read_at", sa.text("created_at DESC")],
    )

    # 4 — automation_log (the one new table).
    op.create_table(
        "automation_log",
        sa.Column(
            "id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "account_id",
            _UUID,
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            _UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "activity_inbox_id",
            _UUID,
            sa.ForeignKey("activity_inbox.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("triggered_by_event_type", sa.Text(), nullable=False),
        sa.Column("triggered_by_event_id", _UUID, nullable=False),
        sa.Column("action_taken", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        # One decision per (account, source event) — the dispatcher's idempotency
        # key under the outbox's at-least-once redelivery contract.
        sa.UniqueConstraint(
            "account_id",
            "triggered_by_event_id",
            name="uq_automation_log_account_event",
        ),
    )
    op.create_index(
        "ix_automation_log_account_time",
        "automation_log",
        ["account_id", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_automation_log_account_time", table_name="automation_log")
    op.drop_table("automation_log")
    op.drop_index("ix_activity_account_unread", table_name="activity_inbox")
    op.drop_column("activity_inbox", "source_event_id")
    op.drop_column("activity_inbox", "source_event_type")
    op.drop_column("activity_inbox", "severity")
    op.execute("DROP TYPE IF EXISTS activity_severity")
    # NOTE: enum VALUEs added to activity_type are intentionally NOT removed —
    # Postgres cannot drop an enum value, and rows may already reference them.
    # This matches the project's additive-enum convention.
