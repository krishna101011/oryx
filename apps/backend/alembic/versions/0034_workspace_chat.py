"""Team Chat foundation wave — chat_messages + workspace_chat_reads.

A single workspace-wide channel (no conversation/thread concept yet — that is
explicitly out of scope for this wave). Recon (docs/design-reference has no
chat mockup; WorkspaceAuditLog's own read path is an unpaginated "latest 50"
with no edit/delete semantics) found nothing to reuse structurally, so this
is a new pair of tables rather than an extension of workspace_audit_log:

CREATEs chat_messages — real message storage with soft-delete (deleted_at)
and edit tracking (edited_at). ix_chat_messages_workspace_cursor
(workspace_id, created_at, id) serves the real cursor-paginated poll query
(WHERE workspace_id = :w AND (created_at, id) > (:c, :i) ORDER BY created_at,
id) — a stable compound order so a cursor never skips or duplicates a row on
a timestamp tie (two messages sent in the same request-handling millisecond).

CREATEs workspace_chat_reads — the minimal per-(workspace, account) last-read
marker an unread indicator needs (composite PK, same shape as
alert_preferences' composite key).

Widens activity_type additively with 'chat' (a real notification category, so
a new chat message can route through the existing, already-proven
NotificationDispatcher — see services/activity/dispatcher.py's CATALOG and
services/activity/preferences.py's NOTIFICATION_CATEGORIES) — same ADD VALUE
IF NOT EXISTS pattern as migration 0014, safe because no row in THIS
migration writes the new value (the transaction-timing trap only bites when a
migration ADDs a value and USEs it in the same alembic upgrade invocation).

Revision ID: 0034_workspace_chat
Revises: 0033_audit_previous_role
Create Date: 2026-07-27
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0034_workspace_chat"
down_revision = "0033_audit_previous_role"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "chat_messages",
        sa.Column(
            "id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "workspace_id", _UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "sender_account_id", _UUID,
            sa.ForeignKey("accounts.id"), nullable=False,
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_chat_messages_workspace_cursor",
        "chat_messages",
        ["workspace_id", "created_at", "id"],
    )

    op.create_table(
        "workspace_chat_reads",
        sa.Column(
            "workspace_id", _UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True,
        ),
        sa.Column(
            "account_id", _UUID,
            sa.ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True,
        ),
        sa.Column(
            "last_read_message_id", _UUID,
            sa.ForeignKey("chat_messages.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Additive widen — see module docstring for why this is safe here.
    op.execute("ALTER TYPE activity_type ADD VALUE IF NOT EXISTS 'chat'")


def downgrade() -> None:
    op.drop_table("workspace_chat_reads")
    op.drop_index("ix_chat_messages_workspace_cursor", table_name="chat_messages")
    op.drop_table("chat_messages")
    # NOTE: the 'chat' activity_type enum VALUE is intentionally NOT removed —
    # Postgres cannot drop an enum value, and rows may already reference it
    # (same convention as migration 0014).
