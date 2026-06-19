"""Phase 5 Wave A — content drafts + versions + citations.

Creates:
  content_drafts    one AI-generated draft per research packet (the create layer)
  draft_versions    append-only edit history — every save/regenerate inserts one
  draft_citations   provenance: which intelligence objects a draft drew from

content_drafts carries UNIQUE (workspace_id, packet_id): exactly ONE draft per
packet (invariant — the generate idempotency target, mirrors intelligence_objects'
UNIQUE(workspace_id, intake_item_id)). The blueprint listed this pair as a plain
index; it is promoted to a uniqueness constraint so the one-draft-per-packet rule
is race-safe (ON CONFLICT DO NOTHING on insert).

template_id is a nullable UUID with NO foreign key in this wave — content_templates
does not exist until migration 0010 (Wave B), which will add the FK.

Revision ID: 0009_phase5_wave_a
Revises: 0008_phase4_wave_e
Create Date: 2026-06-16
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0009_phase5_wave_a"
down_revision = "0008_phase4_wave_e"
branch_labels = None
depends_on = None

CONTENT_FORMAT = sa.Enum(
    "tweet_thread",
    "linkedin_post",
    "newsletter_section",
    "article",
    "report_summary",
    "custom",
    name="content_format_enum",
)
DRAFT_STATUS = sa.Enum(
    "draft",
    "in_review",
    "changes_requested",
    "approved",
    "scheduled",
    "published",
    "rejected",
    "archived",
    name="draft_status_enum",
)

_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    # ---------------- content_drafts ----------------
    op.create_table(
        "content_drafts",
        sa.Column(
            "id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "workspace_id",
            _UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("account_id", _UUID, sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column(
            "packet_id",
            _UUID,
            sa.ForeignKey("research_packets.id"),
            nullable=False,
        ),
        # FK to content_templates is added in migration 0010 (Wave B), where the
        # table is created. Nullable UUID only for now.
        sa.Column("template_id", _UUID),
        sa.Column("format", CONTENT_FORMAT, nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column(
            "status", DRAFT_STATUS, nullable=False, server_default="draft"
        ),
        sa.Column(
            "current_version", sa.Integer(), nullable=False, server_default="1"
        ),
        sa.Column("generation_model", sa.Text(), nullable=False),
        sa.Column("generation_version", sa.Integer(), nullable=False),
        sa.Column("word_count", sa.Integer()),
        sa.Column("published_at", sa.DateTime(timezone=True)),
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
        # Invariant: one draft per packet. The generate path upserts via this
        # constraint's index elements (ON CONFLICT DO NOTHING).
        sa.UniqueConstraint(
            "workspace_id", "packet_id", name="uq_content_drafts_packet"
        ),
    )
    op.create_index(
        "idx_drafts_workspace_status",
        "content_drafts",
        ["workspace_id", "status"],
    )
    op.create_index(
        "idx_drafts_workspace_time",
        "content_drafts",
        ["workspace_id", sa.text("created_at DESC")],
    )

    # ---------------- draft_versions ----------------
    op.create_table(
        "draft_versions",
        sa.Column(
            "id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "draft_id",
            _UUID,
            sa.ForeignKey("content_drafts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_html", sa.Text()),
        sa.Column("edited_by", _UUID, sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("edit_note", sa.Text()),
        sa.Column("word_count", sa.Integer()),
        sa.Column("token_count", sa.Integer()),
        sa.Column(
            "is_ai_generated",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        # Append-only ordering guard: a version number is unique within a draft,
        # so a duplicated append collides instead of silently forking history.
        sa.UniqueConstraint(
            "draft_id", "version_number", name="uq_draft_versions_number"
        ),
    )
    op.create_index(
        "idx_draft_versions_draft",
        "draft_versions",
        ["draft_id", sa.text("version_number DESC")],
    )

    # ---------------- draft_citations ----------------
    op.create_table(
        "draft_citations",
        sa.Column(
            "draft_id",
            _UUID,
            sa.ForeignKey("content_drafts.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "intelligence_object_id",
            _UUID,
            sa.ForeignKey("intelligence_objects.id"),
            primary_key=True,
        ),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_draft_citations_object",
        "draft_citations",
        ["intelligence_object_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_draft_citations_object", table_name="draft_citations")
    op.drop_table("draft_citations")
    op.drop_index("idx_draft_versions_draft", table_name="draft_versions")
    op.drop_table("draft_versions")
    op.drop_index("idx_drafts_workspace_time", table_name="content_drafts")
    op.drop_index("idx_drafts_workspace_status", table_name="content_drafts")
    op.drop_table("content_drafts")
    DRAFT_STATUS.drop(op.get_bind(), checkfirst=True)
    CONTENT_FORMAT.drop(op.get_bind(), checkfirst=True)
