"""Phase 4 Wave B — evidence collection and linking.

Creates:
  evidence              — corpus passages attached to claims
  claim_evidence_links  — typed, strength-scored claim↔evidence edges

No Phase 3 schema changes; the FTS GIN index this wave queries was
created in 0004.

Revision ID: 0005_phase4_wave_b
Revises: 0004_phase4_wave_a
Create Date: 2026-06-11
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005_phase4_wave_b"
down_revision = "0004_phase4_wave_a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------- evidence ----------------
    op.create_table(
        "evidence",
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
            "intake_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("intake_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "evidence_type",
            sa.Enum(
                "corroboration", "contradiction", "context",
                "primary_source", "secondary_source", "inference",
                name="evidence_type",
            ),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "source_deleted", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_evidence_workspace_intake", "evidence", ["workspace_id", "intake_item_id"]
    )

    # ---------------- claim_evidence_links ----------------
    op.create_table(
        "claim_evidence_links",
        sa.Column(
            "claim_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("claims.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "evidence_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evidence.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "relationship",
            sa.Enum(
                "supports", "contradicts", "contextualizes",
                name="evidence_relationship",
            ),
            nullable=False,
        ),
        sa.Column("strength", sa.Float(), nullable=False),
        sa.Column("linker_version", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "strength >= 0.0 AND strength <= 1.0",
            name="ck_claim_evidence_links_strength",
        ),
    )
    op.create_index(
        "idx_claim_evidence_links_claim", "claim_evidence_links", ["claim_id"]
    )
    op.create_index(
        "idx_claim_evidence_links_evidence", "claim_evidence_links", ["evidence_id"]
    )


def downgrade() -> None:
    op.drop_index("idx_claim_evidence_links_evidence", table_name="claim_evidence_links")
    op.drop_index("idx_claim_evidence_links_claim", table_name="claim_evidence_links")
    op.drop_table("claim_evidence_links")
    op.drop_index("idx_evidence_workspace_intake", table_name="evidence")
    op.drop_table("evidence")
    sa.Enum(name="evidence_relationship").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="evidence_type").drop(op.get_bind(), checkfirst=True)
