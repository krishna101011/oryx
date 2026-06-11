"""Phase 3 Wave F — workspace deletion cascade support (CR-6).

Adds `workspace_deletion_orphan_credentials`: the ops holding pen for
credentials whose upstream revoke failed during a workspace deletion
(§17.2). Local credentials are still deleted; this table is what the
operator works through manually.

Revision ID: 0003_phase3_wave_f
Revises: 0002_phase3_baseline
Create Date: 2026-06-11
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_phase3_wave_f"
down_revision = "0002_phase3_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspace_deletion_orphan_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        # No FK: by the time this row exists, the workspace row is being
        # hard-deleted. These are forensic pointers, not relational data.
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("intake_source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_kind", sa.Text(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_orphan_creds_unresolved",
        "workspace_deletion_orphan_credentials",
        ["created_at"],
        postgresql_where=sa.text("resolved_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_orphan_creds_unresolved",
        table_name="workspace_deletion_orphan_credentials",
    )
    op.drop_table("workspace_deletion_orphan_credentials")
