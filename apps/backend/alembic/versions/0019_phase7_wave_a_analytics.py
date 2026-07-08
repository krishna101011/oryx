"""Phase 7 Wave A — analytics_events_raw + analytics_rollups_daily (ADR-047).

analytics_events_raw is Source A of the frozen two-source model: one
lightweight fact per delivered bus event. `source_event_id` is the event
envelope's own id — which IS the outbox row's id (queue/outbox.py builds
OutboxEvent(id=uuid.UUID(event["id"]))) — under a UNIQUE constraint, so the
bus's at-least-once redelivery contract turns into a safe insert-conflict
no-op, the same principle as automation_log's decision key.

analytics_rollups_daily is the single read model: one row per
(workspace_id, metric_key, date), UNIQUE across those three so a rollup
refresh is an UPSERT of a freshly recomputed value, never an accumulate.
The table is sparse — zero-activity days write no row.

NO additional index (the 0014/0015 justify-or-don't rule):
- analytics_events_raw is read ONLY by the rollup worker's full-table
  GROUP BY (workspace_id, event_name, day) recompute — a sequential scan by
  design, which no secondary index helps. Writes hit the source_event_id
  unique index only.
- analytics_rollups_daily's unique constraint's backing btree (workspace_id,
  metric_key, date) already serves both the worker's upsert conflict target
  and Wave B's dashboard reads (workspace_id prefix + range on date after
  equality on metric_key). A separate index would duplicate its prefix.

Revision ID: 0019_phase7_wave_a_analytics
Revises: 0018_phase6_wave_c_flag
Create Date: 2026-07-08
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0019_phase7_wave_a_analytics"
down_revision = "0018_phase6_wave_c_flag"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "analytics_events_raw",
        sa.Column(
            "id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "workspace_id",
            _UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # The delivered envelope's id == the outbox row's id: the dedup key.
        sa.Column("source_event_id", _UUID, nullable=False, unique=True),
        sa.Column("event_name", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "analytics_rollups_daily",
        sa.Column(
            "id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "workspace_id",
            _UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("metric_key", sa.Text(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        # Refresh = upsert on this key, never accumulate (ADR-047).
        sa.UniqueConstraint(
            "workspace_id",
            "metric_key",
            "date",
            name="uq_analytics_rollups_ws_metric_date",
        ),
    )


def downgrade() -> None:
    op.drop_table("analytics_rollups_daily")
    op.drop_table("analytics_events_raw")
