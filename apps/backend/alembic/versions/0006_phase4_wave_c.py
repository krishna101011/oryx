"""Phase 4 Wave C — verification engine, confidence scoring, source credibility.

Creates:
  verification_runs           per-claim, versioned, append-only scoring passes
  source_credibility_records  per-(workspace, source) running accuracy record
  verification_audit_log      append-only Phase 4 pipeline decision log

Plus the source-credibility bootstrap (ADR-031).

Bootstrap note — DEVIATION from the Rev 3 blueprint's illustrative SQL:
  The blueprint (§7.2) joins `workspace_sources.source_id` to
  `source_catalog.id`. Those columns do not exist in the frozen Phase 2
  schema: `source_catalog` is keyed by TEXT `key`, and `workspace_sources`
  references it by TEXT `source_key`. Moreover the runtime `source_id` a
  claim traces to is `intake_items.intake_source_id` (UUID → intake_sources.id),
  not a catalog key. So credibility is keyed by `intake_sources.id` and
  bootstrapped from the catalog's editorial_confidence via
  `intake_sources.origin_catalog_key`.

  The `::float` cast is mandatory and load-bearing: `75 / 100` is integer
  division = 0 in Postgres. `COALESCE(...)::float / 100.0` yields 0.75
  (ADR-031 R9). NULL/custom origin → neutral prior 0.5.

Revision ID: 0006_phase4_wave_c
Revises: 0005_phase4_wave_b
Create Date: 2026-06-13
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006_phase4_wave_c"
down_revision = "0005_phase4_wave_b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------- verification_runs ----------------
    op.create_table(
        "verification_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "claim_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("claims.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "running", "complete", "failed",
                name="verification_status",
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "outcome",
            sa.Enum(
                "verified", "unverified", "contested", "unverifiable",
                name="verification_outcome",
            ),
        ),
        sa.Column("source_trust_score", sa.Float()),
        sa.Column("cross_reference_count", sa.Integer()),
        sa.Column("evidence_strength", sa.Float()),
        sa.Column("recency_score", sa.Float()),
        sa.Column("claim_specificity", sa.Float()),
        sa.Column("primary_source_flag", sa.Boolean()),
        sa.Column("confidence_score", sa.Float()),
        sa.Column("factors", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("engine_version", sa.Integer(), nullable=False),
        sa.Column("scoring_version", sa.Integer(), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "idx_verification_runs_claim",
        "verification_runs",
        ["claim_id", sa.text("engine_version DESC")],
    )
    op.create_index(
        "idx_verification_runs_pending",
        "verification_runs",
        ["status"],
        postgresql_where=sa.text("status = 'pending'"),
    )

    # ---------------- source_credibility_records ----------------
    op.create_table(
        "source_credibility_records",
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        # source_id == intake_sources.id. Not an FK: credibility outlives a
        # source the operator disconnects, and the workspace cascade already
        # removes these rows.
        sa.Column("source_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("accuracy_rate", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("verified_claim_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("contested_claim_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_claim_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bias_indicators", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("topic_reliability", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("last_evaluated_at", sa.DateTime(timezone=True)),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ---------------- verification_audit_log ----------------
    op.create_table(
        "verification_audit_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        # No FK on workspace_id: append-only, must survive workspace delete
        # for historical audit (mirrors auth_audit_log's posture).
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True)),  # NULL = system
        sa.Column("event", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("data", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_verification_audit_ws_time",
        "verification_audit_log",
        ["workspace_id", sa.text("created_at DESC")],
    )

    # ---------------- source credibility bootstrap (ADR-031) ----------------
    # Schema-correct join (see module docstring). `::float` cast is mandatory.
    op.execute(
        """
        INSERT INTO source_credibility_records
            (workspace_id, source_id, accuracy_rate, updated_at)
        SELECT s.workspace_id,
               s.id,
               COALESCE(sc.editorial_confidence, 50)::float / 100.0,
               NOW()
        FROM intake_sources s
        LEFT JOIN source_catalog sc
               ON s.origin_kind = 'catalog'
              AND sc.key = s.origin_catalog_key
        WHERE s.deleted_at IS NULL
        ON CONFLICT (workspace_id, source_id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index("idx_verification_audit_ws_time", table_name="verification_audit_log")
    op.drop_table("verification_audit_log")
    op.drop_table("source_credibility_records")
    op.drop_index("idx_verification_runs_pending", table_name="verification_runs")
    op.drop_index("idx_verification_runs_claim", table_name="verification_runs")
    op.drop_table("verification_runs")
    sa.Enum(name="verification_outcome").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="verification_status").drop(op.get_bind(), checkfirst=True)
