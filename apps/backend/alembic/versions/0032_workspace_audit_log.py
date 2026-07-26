"""Team nav promotion wave — workspace_audit_log, the real audit trail behind
the new top-level Team section's Activity view.

No existing infrastructure covered this: AuthAuditLog (core/audit.py) is
account-scoped auth security events, never workspace-scoped and never read
back by any endpoint; activity_inbox is a personal notification inbox keyed
to ActivityType, not a per-workspace membership log. This table is a new,
minimal, write-then-list audit trail, following AuthAuditLog's exact shape
(plain Text `event` column, not a Postgres enum — sidesteps the ADD VALUE
single-transaction trap a real enum would hit the first time a future event
kind is added). Rows are inserted inside the same transaction as the
membership change itself (see services/workspaces/repository.py's
record_activity), never a separate commit.

Revision ID: 0032_workspace_audit_log
Revises: 0031_team_workspace_rev2
Create Date: 2026-07-26
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0032_workspace_audit_log"
down_revision = "0031_team_workspace_rev2"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "workspace_audit_log",
        sa.Column(
            "id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "workspace_id", _UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("event", sa.Text(), nullable=False),
        sa.Column("actor_account_id", _UUID, sa.ForeignKey("accounts.id"), nullable=True),
        sa.Column("subject_account_id", _UUID, sa.ForeignKey("accounts.id"), nullable=True),
        sa.Column("subject_email", sa.Text(), nullable=True),
        sa.Column("role", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.func.now(),
        ),
    )
    # The Team Activity view always queries "latest N for this workspace" —
    # same access shape as ix_workspace_invites_workspace.
    op.create_index(
        "ix_workspace_audit_log_workspace_created",
        "workspace_audit_log",
        ["workspace_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_workspace_audit_log_workspace_created", table_name="workspace_audit_log")
    op.drop_table("workspace_audit_log")
