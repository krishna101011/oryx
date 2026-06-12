"""Phase 4 Wave A — claim extraction + epistemic typing.

Creates:
  claims               — atomic assertions extracted from normalized items
  workspace_ai_budget  — per-workspace daily AI token budget ledger

Plus an additive full-text index on intake_items_normalized (index only —
no Phase 3 schema change).

Revision ID: 0004_phase4_wave_a
Revises: 0003_phase3_wave_f
Create Date: 2026-06-11
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_phase4_wave_a"
down_revision = "0003_phase3_wave_f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------- claims ----------------
    op.create_table(
        "claims",
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
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("predicate", sa.Text(), nullable=False),
        sa.Column("object", sa.Text()),
        sa.Column(
            "epistemic_type",
            sa.Enum(
                "fact", "claim", "rumor", "speculation", "opinion", "unclassified",
                name="epistemic_type",
            ),
            nullable=False,
            server_default="unclassified",
        ),
        sa.Column("extractor_version", sa.Integer(), nullable=False),
        sa.Column("classifier_version", sa.Integer()),
        sa.Column(
            "requires_analyst_review",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "superseded_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("claims.id"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        # Idempotency guard: duplicate extraction of the same claim text from
        # the same item is a silent no-op (ON CONFLICT DO NOTHING).
        sa.UniqueConstraint(
            "workspace_id", "intake_item_id", "text",
            name="uq_claims_workspace_item_text",
        ),
    )
    op.create_index(
        "idx_claims_workspace_intake", "claims", ["workspace_id", "intake_item_id"]
    )
    op.create_index("idx_claims_subject", "claims", ["workspace_id", "subject"])
    op.create_index(
        "idx_claims_epistemic_type", "claims", ["workspace_id", "epistemic_type"]
    )

    # ---------------- workspace_ai_budget ----------------
    op.create_table(
        "workspace_ai_budget",
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("budget_date", sa.Date(), primary_key=True),
        sa.Column("tokens_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("budget_limit", sa.Integer(), nullable=False, server_default="100000"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ---------------- additive FTS index on a Phase 3 table ----------------
    # Index only — NOT a schema change to intake_items_normalized.
    op.create_index(
        "idx_intake_normalized_fts",
        "intake_items_normalized",
        [
            sa.text(
                "to_tsvector('english', "
                "coalesce(subject,'') || ' ' || coalesce(body_text,''))"
            )
        ],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("idx_intake_normalized_fts", table_name="intake_items_normalized")
    op.drop_table("workspace_ai_budget")
    op.drop_index("idx_claims_epistemic_type", table_name="claims")
    op.drop_index("idx_claims_subject", table_name="claims")
    op.drop_index("idx_claims_workspace_intake", table_name="claims")
    op.drop_table("claims")
    sa.Enum(name="epistemic_type").drop(op.get_bind(), checkfirst=True)
