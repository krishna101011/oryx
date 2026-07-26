"""Role-change wave — workspace_audit_log.previous_role.

PATCH /v1/workspaces/members/{accountId} finally emits the reserved
'role_changed' event (see services/workspaces/repository.py record_activity).
The existing `role` column follows the established convention of carrying
the role meaningfully associated with the subject AFTER the event
(invited-as, joined-as, removed-from) — for role_changed that's the NEW
role. A real audit trail needs the OLD role too, so this adds a second
nullable Text column rather than overloading `role` or packing both values
into one string. Plain ADD COLUMN, no enum involved — none of the ADD VALUE
transaction-timing traps documented for workspace_role/workspace_plan apply
here (see 0029/0030 docstrings).

Revision ID: 0033_audit_previous_role
Revises: 0032_workspace_audit_log
Create Date: 2026-07-27
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0033_audit_previous_role"
down_revision = "0032_workspace_audit_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workspace_audit_log", sa.Column("previous_role", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("workspace_audit_log", "previous_role")
