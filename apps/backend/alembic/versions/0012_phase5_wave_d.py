"""Phase 5 Wave D — publish targets + publications (channel delivery).

Creates:
  publish_channel_enum      twitter_x | linkedin | email_newsletter | notion |
                            webhook | export
  publication_status_enum   pending | delivering | delivered | failed | cancelled

  publish_targets   per-workspace channel config. `credentials` + `credentials_iv`
                    hold the AES-256-GCM ciphertext/IV — never read at the API edge.
  publications      one row per (draft, version, target) delivery attempt.

The idempotency guarantee is the DB itself: uq_publications_draft_version_target
is UNIQUE on (draft_id, version_number, target_id). Two delivered publications for
the same draft+version+target can never coexist — the engine inserts with
ON CONFLICT DO NOTHING and re-reads the winner (§16.2).

Revision ID: 0012_phase5_wave_d
Revises: 0011_phase5_wave_c
Create Date: 2026-06-23
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0012_phase5_wave_d"
down_revision = "0011_phase5_wave_c"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)

# Enums created via raw SQL before the tables; create_type=False stops
# create_table from re-emitting them (the same approach Wave C used).
_CHANNEL_ENUM = postgresql.ENUM(
    "twitter_x",
    "linkedin",
    "email_newsletter",
    "notion",
    "webhook",
    "export",
    name="publish_channel_enum",
    create_type=False,
)
_PUB_STATUS_ENUM = postgresql.ENUM(
    "pending",
    "delivering",
    "delivered",
    "failed",
    "cancelled",
    name="publication_status_enum",
    create_type=False,
)


def upgrade() -> None:
    # 1 — enums
    op.execute(
        "CREATE TYPE publish_channel_enum AS ENUM "
        "('twitter_x', 'linkedin', 'email_newsletter', 'notion', "
        "'webhook', 'export')"
    )
    op.execute(
        "CREATE TYPE publication_status_enum AS ENUM "
        "('pending', 'delivering', 'delivered', 'failed', 'cancelled')"
    )

    # 2 — publish_targets
    op.create_table(
        "publish_targets",
        sa.Column(
            "id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "workspace_id",
            _UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("channel", _CHANNEL_ENUM, nullable=False),
        # AES-256-GCM ciphertext + per-record 12-byte IV. Write-only at the API.
        sa.Column("credentials", sa.LargeBinary(), nullable=False),
        sa.Column("credentials_iv", sa.LargeBinary(), nullable=False),
        sa.Column(
            "config",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("last_health_at", sa.DateTime(timezone=True)),
        sa.Column("last_health_ok", sa.Boolean()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_publish_targets_workspace_channel",
        "publish_targets",
        ["workspace_id", "channel"],
    )
    op.create_index(
        "idx_publish_targets_active",
        "publish_targets",
        ["workspace_id"],
        postgresql_where=sa.text("is_active = true"),
    )

    # 3 — publications
    op.create_table(
        "publications",
        sa.Column(
            "id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "draft_id",
            _UUID,
            sa.ForeignKey("content_drafts.id"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column(
            "target_id",
            _UUID,
            sa.ForeignKey("publish_targets.id"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            _UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            _PUB_STATUS_ENUM,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("external_id", sa.Text()),
        sa.Column("external_url", sa.Text()),
        sa.Column("error_message", sa.Text()),
        sa.Column(
            "attempt_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("scheduled_at", sa.DateTime(timezone=True)),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        # THE idempotency mechanism (§16.2): the DB prevents two publications for
        # the same draft+version+target. The engine relies on this for ON CONFLICT.
        sa.UniqueConstraint(
            "draft_id",
            "version_number",
            "target_id",
            name="uq_publications_draft_version_target",
        ),
    )
    op.create_index("idx_publications_draft", "publications", ["draft_id"])
    op.create_index(
        "idx_publications_workspace_status",
        "publications",
        ["workspace_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_publications_workspace_status", table_name="publications"
    )
    op.drop_index("idx_publications_draft", table_name="publications")
    op.drop_table("publications")
    op.drop_index("idx_publish_targets_active", table_name="publish_targets")
    op.drop_index(
        "idx_publish_targets_workspace_channel", table_name="publish_targets"
    )
    op.drop_table("publish_targets")
    op.execute("DROP TYPE IF EXISTS publication_status_enum")
    op.execute("DROP TYPE IF EXISTS publish_channel_enum")
