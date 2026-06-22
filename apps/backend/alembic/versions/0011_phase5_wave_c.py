"""Phase 5 Wave C — review workflow + approval.

Creates:
  review_outcome_enum     'approved'|'rejected'|'changes_requested'
  draft_reviews           append-only audit row, one per review action

Indexes:
  idx_draft_reviews_draft  (draft_id, created_at DESC) — latest-first history

`note` is nullable at the DB layer (frozen schema §7.2). The non-empty
requirement for 'rejected'/'changes_requested' is enforced at the service
layer (HTTP 400), the same pattern Wave A/B use for similar field guards.

Revision ID: 0011_phase5_wave_c
Revises: 0010_phase5_wave_b
Create Date: 2026-06-22
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0011_phase5_wave_c"
down_revision = "0010_phase5_wave_b"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)

# New enum — created manually via raw SQL before the table (create_type=False
# stops create_table from re-emitting it).
_OUTCOME_ENUM = postgresql.ENUM(
    "approved",
    "rejected",
    "changes_requested",
    name="review_outcome_enum",
    create_type=False,
)


def upgrade() -> None:
    # 1 — create the outcome enum (raw SQL — most reliable in alembic)
    op.execute(
        "CREATE TYPE review_outcome_enum AS ENUM "
        "('approved', 'rejected', 'changes_requested')"
    )

    # 2 — create draft_reviews
    op.create_table(
        "draft_reviews",
        sa.Column(
            "id",
            _UUID,
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "draft_id",
            _UUID,
            sa.ForeignKey("content_drafts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column(
            "account_id",
            _UUID,
            sa.ForeignKey("accounts.id"),
            nullable=False,
        ),
        sa.Column("outcome", _OUTCOME_ENUM, nullable=False),
        sa.Column("note", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # 3 — latest-first history index
    op.create_index(
        "idx_draft_reviews_draft",
        "draft_reviews",
        ["draft_id", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("idx_draft_reviews_draft", table_name="draft_reviews")
    op.drop_table("draft_reviews")
    op.execute("DROP TYPE IF EXISTS review_outcome_enum")
