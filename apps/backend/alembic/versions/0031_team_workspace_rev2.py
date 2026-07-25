"""Team/Workspace Rev 2 (docs/TEAM_WORKSPACE_ARCHITECTURE.md) — backend
foundation: invite mechanism + the sessions.workspace_id fix that makes
workspace switching actually stick across a token refresh.

sessions.workspace_id (§5.1's real fix): previously nothing persisted which
workspace a session's access tokens were scoped to — refresh() had to
re-derive one from scratch via _primary_workspace_id's arbitrary .limit(1)
every time, silently reverting an explicit workspace switch on the next
refresh cycle. Backfill picks each account's earliest-joined active
membership (deterministic, matches the same-wave fix to
_primary_workspace_id's ORDER BY) — every account today has exactly one
real membership (its own owner row, recon-verified: 278/278 real rows),
so this backfill is exact, not a guess, for all existing data.

workspace_invites (§3): a pending (or resolved) invitation. token_hash is
the SHA-256 hex of a display-once random token, same shape as the intake
webhook secret convention — the raw token is never persisted.

Revision ID: 0031_team_workspace_rev2
Revises: 0030_plan_prices
Create Date: 2026-07-26
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0031_team_workspace_rev2"
down_revision = "0030_plan_prices"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)

_ROLE_ENUM = postgresql.ENUM(
    "owner", "admin", "editor", "reader", name="workspace_role", create_type=False
)


def upgrade() -> None:
    # 1 — sessions.workspace_id: add nullable, backfill, then tighten.
    op.add_column("sessions", sa.Column("workspace_id", _UUID, nullable=True))
    op.execute(
        """
        UPDATE sessions s
        SET workspace_id = (
            SELECT wm.workspace_id
            FROM workspace_members wm
            WHERE wm.account_id = s.account_id
              AND wm.removed_at IS NULL
            ORDER BY wm.joined_at ASC
            LIMIT 1
        )
        """
    )
    op.alter_column("sessions", "workspace_id", nullable=False)
    op.create_foreign_key(
        "fk_sessions_workspace_id",
        "sessions",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 2 — workspace_invites.
    op.create_table(
        "workspace_invites",
        sa.Column(
            "id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "workspace_id", _UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("invited_email", postgresql.CITEXT(), nullable=False),
        sa.Column("role", _ROLE_ENUM, nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False, unique=True),
        sa.Column(
            "invited_by", _UUID, sa.ForeignKey("accounts.id"), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_workspace_invites_workspace", "workspace_invites", ["workspace_id"]
    )
    # Fast lookup for "does this email already have a pending invite here".
    op.create_index(
        "ix_workspace_invites_email_pending",
        "workspace_invites",
        ["workspace_id", "invited_email"],
        postgresql_where=sa.text("accepted_at IS NULL AND revoked_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_workspace_invites_email_pending", table_name="workspace_invites")
    op.drop_index("ix_workspace_invites_workspace", table_name="workspace_invites")
    op.drop_table("workspace_invites")

    op.drop_constraint("fk_sessions_workspace_id", "sessions", type_="foreignkey")
    op.drop_column("sessions", "workspace_id")
