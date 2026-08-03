"""Public Reader Rev 1 — public_pages + public_page_citations.

Creates public_pages: one row per ContentDraft that has ever reached
'published', created automatically by the publishing engine in the same
transaction as the draft's status transition (never a direct API write).
UNIQUE(content_draft_id) is the schema-level "exactly one page per draft"
guarantee; UNIQUE(slug) backs the opaque public identifier.

Creates public_page_citations: the provenance snapshot for a public page's
cited intelligence objects, deliberately a SEPARATE table from
publication_citations (never joined to it) so the public repository method
serving GET /public/pages/{slug} can select only these two tables' own
columns and is structurally unable to reach intelligence_objects, claims, or
any other workspace-internal table (docs/PUBLIC_READER_ARCHITECTURE.md §6).

Reuses the existing epistemic_type enum (create_type=False), same as
0021_publication_citations.

Revision ID: 0035_public_pages
Revises: 0034_workspace_chat
Create Date: 2026-08-03
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0035_public_pages"
down_revision = "0034_workspace_chat"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)

_EPISTEMIC_ENUM = postgresql.ENUM(
    "fact",
    "claim",
    "rumor",
    "speculation",
    "opinion",
    "unclassified",
    name="epistemic_type",
    create_type=False,
)


def upgrade() -> None:
    op.create_table(
        "public_pages",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column(
            "content_draft_id",
            _UUID,
            sa.ForeignKey("content_drafts.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "workspace_id",
            _UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("slug", sa.Text(), nullable=False, unique=True),
        sa.Column("content_snapshot", sa.Text(), nullable=False),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_public_pages_workspace", "public_pages", ["workspace_id"]
    )

    op.create_table(
        "public_page_citations",
        sa.Column(
            "public_page_id",
            _UUID,
            sa.ForeignKey("public_pages.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "intelligence_object_id",
            _UUID,
            sa.ForeignKey("intelligence_objects.id"),
            primary_key=True,
        ),
        sa.Column("headline", sa.Text(), nullable=False),
        sa.Column("epistemic_type", _EPISTEMIC_ENUM, nullable=False),
        sa.Column("confidence_score", sa.Float()),
        sa.Column("scoring_version", sa.Integer(), nullable=False),
        sa.Column(
            "snapshotted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("public_page_citations")
    op.drop_index("idx_public_pages_workspace", table_name="public_pages")
    op.drop_table("public_pages")
