"""Phase 5 Wave B — content_templates + FK + backfill.

Creates:
  content_tone_enum       'formal'|'analytical'|'conversational'|'authoritative'|'concise'
  content_templates       one default row per format per workspace (lazy-seeded)

Alters:
  content_drafts.template_id  adds FK → content_templates(id)

Indexes:
  idx_templates_workspace_format       regular (supports list queries)
  uq_templates_one_default_per_format  partial UNIQUE WHERE is_default=true
    — the idempotency target for ON CONFLICT DO NOTHING inserts; guarantees
      at most one default per (workspace, format) at the DB layer.

Backfill inserts 6 default rows per existing workspace, one per
content_format_enum value. ON CONFLICT DO NOTHING makes re-running safe.

Revision ID: 0010_phase5_wave_b
Revises: 0009_phase5_wave_a
Create Date: 2026-06-21
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010_phase5_wave_b"
down_revision = "0009_phase5_wave_a"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)

# Existing enum — create_type=False prevents re-creation within create_table.
_FORMAT_ENUM = postgresql.ENUM(
    "tweet_thread",
    "linkedin_post",
    "newsletter_section",
    "article",
    "report_summary",
    "custom",
    name="content_format_enum",
    create_type=False,
)
# New enum — we create it manually via raw SQL before the table.
_TONE_ENUM = postgresql.ENUM(
    "formal",
    "analytical",
    "conversational",
    "authoritative",
    "concise",
    name="content_tone_enum",
    create_type=False,
)

# Seed rows — tone/max_words/min_words/structure_hint mirror FORMAT_GUIDANCE
# from services/drafts/models.py, shaped into structured template fields.
_SEED: list[tuple[str, str, int | None, int | None, str]] = [
    # (format, tone, max_words, min_words, structure_hint)
    (
        "tweet_thread",
        "conversational",
        None,
        None,
        "Number each tweet (1/N, 2/N...). Max 280 characters per tweet. Punchy, conversational.",
    ),
    (
        "linkedin_post",
        "authoritative",
        500,
        None,
        "Professional tone. Paragraphs, not bullet lists. Max 3000 characters.",
    ),
    (
        "newsletter_section",
        "analytical",
        500,
        200,
        "Structured. Clear headline followed by body. Max 500 words.",
    ),
    (
        "article",
        "analytical",
        3000,
        800,
        "Long-form. Headline plus subheadings. 800 to 3000 words.",
    ),
    (
        "report_summary",
        "concise",
        400,
        200,
        "Executive format. Key points stated directly. 200 to 400 words.",
    ),
    (
        "custom",
        "analytical",
        None,
        None,
        "No fixed constraints. Follow analyst instructions exactly.",
    ),
]


def upgrade() -> None:
    # 1 — create the tone enum (raw SQL — most reliable in alembic)
    op.execute(
        "CREATE TYPE content_tone_enum AS ENUM "
        "('formal', 'analytical', 'conversational', 'authoritative', 'concise')"
    )

    # 2 — create content_templates
    op.create_table(
        "content_templates",
        sa.Column(
            "id",
            _UUID,
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "workspace_id",
            _UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("format", _FORMAT_ENUM, nullable=False),
        sa.Column("tone", _TONE_ENUM, nullable=False, server_default="analytical"),
        sa.Column("max_words", sa.Integer()),
        sa.Column("min_words", sa.Integer()),
        sa.Column("structure_hint", sa.Text()),
        sa.Column(
            "is_default",
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
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # regular index — supports list queries by workspace+format
    op.create_index(
        "idx_templates_workspace_format",
        "content_templates",
        ["workspace_id", "format"],
    )

    # partial UNIQUE index — the data-integrity guarantee for defaults.
    # ON CONFLICT on this index is the idempotency mechanism for seeding.
    op.execute(
        """
        CREATE UNIQUE INDEX uq_templates_one_default_per_format
        ON content_templates (workspace_id, format)
        WHERE is_default = TRUE
        """
    )

    # 3 — add FK from content_drafts.template_id → content_templates
    op.create_foreign_key(
        "fk_content_drafts_template",
        "content_drafts",
        "content_templates",
        ["template_id"],
        ["id"],
    )

    # 4 — backfill one default template per format per existing workspace.
    #     ON CONFLICT on the partial unique index → DO NOTHING (re-run safe).
    conn = op.get_bind()
    workspace_ids = [
        row[0]
        for row in conn.execute(sa.text("SELECT id FROM workspaces")).fetchall()
    ]
    for ws_id in workspace_ids:
        for fmt, tone, max_w, min_w, hint in _SEED:
            conn.execute(
                sa.text(
                    """
                    INSERT INTO content_templates
                        (workspace_id, name, format, tone,
                         max_words, min_words, structure_hint, is_default)
                    VALUES
                        (:ws, :name, CAST(:fmt AS content_format_enum),
                         CAST(:tone AS content_tone_enum),
                         :max_w, :min_w, :hint, TRUE)
                    ON CONFLICT (workspace_id, format)
                    WHERE is_default = TRUE
                    DO NOTHING
                    """
                ),
                {
                    "ws": str(ws_id),
                    "name": f"Default {fmt.replace('_', ' ').title()}",
                    "fmt": fmt,
                    "tone": tone,
                    "max_w": max_w,
                    "min_w": min_w,
                    "hint": hint,
                },
            )


def downgrade() -> None:
    op.drop_constraint("fk_content_drafts_template", "content_drafts", type_="foreignkey")
    op.execute("DROP INDEX IF EXISTS uq_templates_one_default_per_format")
    op.drop_index("idx_templates_workspace_format", table_name="content_templates")
    op.drop_table("content_templates")
    op.execute("DROP TYPE IF EXISTS content_tone_enum")
