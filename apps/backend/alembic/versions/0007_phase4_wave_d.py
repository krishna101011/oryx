"""Phase 4 Wave D — conflict detection, resolution, and analyst review.

Creates:
  conflict_records   per-(workspace, claim pair) detected conflict + resolution
  analyst_reviews    append-only log of every analyst decision

Conflict pairs are stored with CANONICAL ORDERING: claim_a_id is always the
smaller UUID. The service enforces this before every insert so the UNIQUE
(workspace_id, claim_a_id, claim_b_id) constraint dedupes a pair regardless of
which claim's verification triggered detection.

Revision ID: 0007_phase4_wave_d
Revises: 0006_phase4_wave_c
Create Date: 2026-06-13
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007_phase4_wave_d"
down_revision = "0006_phase4_wave_c"
branch_labels = None
depends_on = None

CONFLICT_TYPE = sa.Enum(
    "direct_contradiction",
    "factual_disagreement",
    "temporal_inconsistency",
    "scope_difference",
    name="conflict_type_enum",
)
CONFLICT_STATUS = sa.Enum(
    "open",
    "resolved_a_wins",
    "resolved_b_wins",
    "resolved_inconclusive",
    "resolved_system",
    "analyst_reviewed",
    name="conflict_status_enum",
)
CONFLICT_RESOLVER = sa.Enum("system", "analyst", name="conflict_resolver_enum")
ANALYST_ENTITY = sa.Enum(
    "claim", "intelligence_object", "conflict", name="analyst_entity_enum"
)
ANALYST_OUTCOME = sa.Enum(
    "approved",
    "rejected",
    "flagged",
    "override_verified",
    "override_unverified",
    "conflict_resolved_a",
    "conflict_resolved_b",
    "conflict_inconclusive",
    name="analyst_outcome_enum",
)


def upgrade() -> None:
    # ---------------- conflict_records ----------------
    op.create_table(
        "conflict_records",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "claim_a_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("claims.id"),
            nullable=False,
        ),
        sa.Column(
            "claim_b_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("claims.id"),
            nullable=False,
        ),
        sa.Column("conflict_type", CONFLICT_TYPE, nullable=False),
        sa.Column("severity", sa.Float(), nullable=False),
        sa.Column(
            "status", CONFLICT_STATUS, nullable=False, server_default="open"
        ),
        sa.Column("resolution_note", sa.Text()),
        sa.Column(
            "resolved_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounts.id"),
        ),
        sa.Column("resolved_by_kind", CONFLICT_RESOLVER),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        # Canonical ordering (smaller UUID = claim_a_id) is enforced in the
        # service so this UNIQUE dedupes a pair from either detection direction.
        sa.UniqueConstraint(
            "workspace_id",
            "claim_a_id",
            "claim_b_id",
            name="uq_conflict_records_pair",
        ),
    )
    op.create_index(
        "idx_conflict_records_open",
        "conflict_records",
        ["workspace_id"],
        postgresql_where=sa.text("status = 'open'"),
    )
    # Pair-lookup index (spec §STEP1.4). Overlaps the UNIQUE index above but
    # kept as the named access path the detection query plans against.
    op.create_index(
        "idx_conflict_records_claims",
        "conflict_records",
        ["workspace_id", "claim_a_id", "claim_b_id"],
    )

    # ---------------- analyst_reviews ----------------
    op.create_table(
        "analyst_reviews",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounts.id"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entity_type", ANALYST_ENTITY, nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("outcome", ANALYST_OUTCOME, nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_analyst_reviews_entity",
        "analyst_reviews",
        ["workspace_id", "entity_type", "entity_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_analyst_reviews_entity", table_name="analyst_reviews")
    op.drop_table("analyst_reviews")
    op.drop_index("idx_conflict_records_claims", table_name="conflict_records")
    op.drop_index("idx_conflict_records_open", table_name="conflict_records")
    op.drop_table("conflict_records")
    ANALYST_OUTCOME.drop(op.get_bind(), checkfirst=True)
    ANALYST_ENTITY.drop(op.get_bind(), checkfirst=True)
    CONFLICT_RESOLVER.drop(op.get_bind(), checkfirst=True)
    CONFLICT_STATUS.drop(op.get_bind(), checkfirst=True)
    CONFLICT_TYPE.drop(op.get_bind(), checkfirst=True)
