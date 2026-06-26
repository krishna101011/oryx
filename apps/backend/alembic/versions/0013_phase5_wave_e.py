"""Phase 5 Wave E — content calendar + scheduling.

Creates:
  calendar_status_enum   scheduled | published | cancelled | failed

  calendar_entries   one row per (draft, target) explicit schedule. The
                     CalendarScheduler (services/calendar/scheduler.py) polls
                     status='scheduled' rows whose scheduled_at has arrived and
                     fires them through the EXISTING publishing engine.

Also ALTERs publications:
  + last_attempt_at timestamptz NULL — records WHEN the last transient attempt
    happened (attempt_count records HOW MANY). Wave D's migration should have had
    this; without it the Pass-B retry re-drive cannot compute "enough backoff
    has elapsed". The engine's transient-failure path now stamps it (§16.3).

The partial index idx_calendar_scheduled (WHERE status='scheduled') is what keeps
the scheduler's every-60s polling query cheap — it only ever scans live entries.

Revision ID: 0013_phase5_wave_e
Revises: 0012_phase5_wave_d
Create Date: 2026-06-26
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0013_phase5_wave_e"
down_revision = "0012_phase5_wave_d"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)

# create_type=False so create_table does not re-emit the enum (Wave C/D pattern).
_CALENDAR_STATUS_ENUM = postgresql.ENUM(
    "scheduled",
    "published",
    "cancelled",
    "failed",
    name="calendar_status_enum",
    create_type=False,
)


def upgrade() -> None:
    # 1 — enum
    op.execute(
        "CREATE TYPE calendar_status_enum AS ENUM "
        "('scheduled', 'published', 'cancelled', 'failed')"
    )

    # 2 — calendar_entries
    op.create_table(
        "calendar_entries",
        sa.Column(
            "id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "workspace_id",
            _UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "draft_id",
            _UUID,
            sa.ForeignKey("content_drafts.id"),
            nullable=False,
        ),
        sa.Column(
            "target_id",
            _UUID,
            sa.ForeignKey("publish_targets.id"),
            nullable=False,
        ),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            _CALENDAR_STATUS_ENUM,
            nullable=False,
            server_default="scheduled",
        ),
        sa.Column(
            "publication_id",
            _UUID,
            sa.ForeignKey("publications.id"),
            nullable=True,
        ),
        sa.Column(
            "created_by",
            _UUID,
            sa.ForeignKey("accounts.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        # One schedule per (draft, target) — re-scheduling the same target for a
        # draft is surfaced as a clean error, not a duplicate row.
        sa.UniqueConstraint(
            "draft_id", "target_id", name="uq_calendar_entries_draft_target"
        ),
    )
    op.create_index(
        "idx_calendar_workspace_time",
        "calendar_entries",
        ["workspace_id", "scheduled_at"],
    )
    # Partial index — the scheduler only ever queries live 'scheduled' rows, so
    # the index stays small no matter how much published/cancelled history grows.
    op.create_index(
        "idx_calendar_scheduled",
        "calendar_entries",
        ["scheduled_at"],
        postgresql_where=sa.text("status = 'scheduled'"),
    )

    # 3 — publications.last_attempt_at (the Wave D refinement)
    op.add_column(
        "publications",
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("publications", "last_attempt_at")
    op.drop_index("idx_calendar_scheduled", table_name="calendar_entries")
    op.drop_index("idx_calendar_workspace_time", table_name="calendar_entries")
    op.drop_table("calendar_entries")
    op.execute("DROP TYPE IF EXISTS calendar_status_enum")
