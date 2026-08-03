"""Phase 8 Wave A — Training/Academy schema foundation
(docs/PHASE_8_TRAINING_ARCHITECTURE.md §2).

Creates courses, modules, lessons, enrollments, lesson_progress,
certificates. `courses` deliberately has NO workspace_id column — the
Academy catalog is platform-wide, per §2/§4's corrected reasoning (a
workspace-scoped resource makes no sense for content authored once and
shared by every workspace). Authoring is gated by Account.is_platform_admin
at the application layer (core/dependencies.py's require_platform_admin),
not by any schema-level workspace reference.

Revision ID: 0036_phase8_training_foundation
Revises: 0035_public_pages
Create Date: 2026-08-04
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0036_phase8_training_foundation"
down_revision = "0035_public_pages"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "courses",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column(
            "created_by", _UUID, sa.ForeignKey("accounts.id"), nullable=False
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

    op.create_table(
        "modules",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column(
            "course_id",
            _UUID,
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
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
    op.create_index("idx_modules_course", "modules", ["course_id"])

    op.create_table(
        "lessons",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column(
            "module_id",
            _UUID,
            sa.ForeignKey("modules.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("video_asset_id", sa.Text()),
        sa.Column("transcript_text", sa.Text()),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
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
    op.create_index("idx_lessons_module", "lessons", ["module_id"])

    op.create_table(
        "enrollments",
        sa.Column(
            "account_id",
            _UUID,
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "course_id",
            _UUID,
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "enrolled_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "lesson_progress",
        sa.Column(
            "account_id",
            _UUID,
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "lesson_id",
            _UUID,
            sa.ForeignKey("lessons.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "certificates",
        sa.Column(
            "account_id",
            _UUID,
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "course_id",
            _UUID,
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("certificates")
    op.drop_table("lesson_progress")
    op.drop_table("enrollments")
    op.drop_index("idx_lessons_module", table_name="lessons")
    op.drop_table("lessons")
    op.drop_index("idx_modules_course", table_name="modules")
    op.drop_table("modules")
    op.drop_table("courses")
