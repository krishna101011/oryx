"""Phase 4 Wave E — intelligence objects + research workspaces/packets.

Creates:
  intelligence_objects      the fan-in: N verified claims → one scored object
  research_workspaces       analyst curation surface
  research_workspace_items  objects pinned into a workspace
  research_packets          the Phase 5 handoff bundle

intelligence_objects carries UNIQUE (workspace_id, intake_item_id): exactly one
object per intake item per workspace (the composition upsert target).

Revision ID: 0008_phase4_wave_e
Revises: 0007_phase4_wave_d
Create Date: 2026-06-13
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0008_phase4_wave_e"
down_revision = "0007_phase4_wave_d"
branch_labels = None
depends_on = None

INTEL_STATUS = sa.Enum(
    "unverified",
    "verified",
    "contested",
    "analyst_approved",
    "analyst_rejected",
    name="intel_status_enum",
)
RWS_STATUS = sa.Enum("active", "archived", name="rws_status_enum")
PACKET_STATUS = sa.Enum(
    "assembling", "ready", "consumed", name="packet_status_enum"
)

# Reuse the existing epistemic_type enum (created in migration 0004); do NOT
# re-emit CREATE TYPE for it.
EPISTEMIC_TYPE = postgresql.ENUM(name="epistemic_type", create_type=False)
_UUID = postgresql.UUID(as_uuid=True)
_UUID_ARRAY = postgresql.ARRAY(postgresql.UUID(as_uuid=True))


def upgrade() -> None:
    # ---------------- intelligence_objects ----------------
    op.create_table(
        "intelligence_objects",
        sa.Column(
            "id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "workspace_id",
            _UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "intake_item_id",
            _UUID,
            sa.ForeignKey("intake_items.id"),
            nullable=False,
        ),
        sa.Column("epistemic_type", EPISTEMIC_TYPE, nullable=False),
        sa.Column("confidence_score", sa.Float()),
        sa.Column(
            "verification_status", INTEL_STATUS, nullable=False, server_default="unverified"
        ),
        sa.Column(
            "claim_ids", _UUID_ARRAY, nullable=False, server_default=sa.text("'{}'")
        ),
        sa.Column(
            "conflict_ids", _UUID_ARRAY, nullable=False, server_default=sa.text("'{}'")
        ),
        sa.Column("key_facts", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("headline", sa.Text(), nullable=False),
        sa.Column("scoring_version", sa.Integer(), nullable=False),
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
        sa.UniqueConstraint(
            "workspace_id", "intake_item_id", name="uq_intelligence_objects_item"
        ),
    )
    op.create_index(
        "idx_intelligence_objects_ws_time",
        "intelligence_objects",
        ["workspace_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "idx_intelligence_objects_status",
        "intelligence_objects",
        ["workspace_id", "verification_status"],
    )
    op.create_index(
        "idx_intelligence_objects_score",
        "intelligence_objects",
        ["workspace_id", sa.text("confidence_score DESC")],
    )
    op.create_index(
        "idx_intelligence_objects_headline",
        "intelligence_objects",
        [sa.text("to_tsvector('english', headline)")],
        postgresql_using="gin",
    )
    op.create_index(
        "idx_intelligence_objects_scoring_version",
        "intelligence_objects",
        ["workspace_id", "scoring_version"],
    )

    # ---------------- research_workspaces ----------------
    op.create_table(
        "research_workspaces",
        sa.Column(
            "id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "account_id", _UUID, sa.ForeignKey("accounts.id"), nullable=False
        ),
        sa.Column(
            "workspace_id",
            _UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", RWS_STATUS, nullable=False, server_default="active"),
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

    # ---------------- research_workspace_items ----------------
    op.create_table(
        "research_workspace_items",
        sa.Column(
            "research_workspace_id",
            _UUID,
            sa.ForeignKey("research_workspaces.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "intelligence_object_id",
            _UUID,
            sa.ForeignKey("intelligence_objects.id"),
            primary_key=True,
        ),
        sa.Column(
            "added_by", _UUID, sa.ForeignKey("accounts.id"), nullable=False
        ),
        sa.Column("note", sa.Text()),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "note IS NULL OR length(note) <= 500",
            name="ck_research_ws_items_note_len",
        ),
    )
    op.create_index(
        "idx_research_ws_items",
        "research_workspace_items",
        ["research_workspace_id", sa.text("added_at DESC")],
    )

    # ---------------- research_packets ----------------
    op.create_table(
        "research_packets",
        sa.Column(
            "id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "research_workspace_id",
            _UUID,
            sa.ForeignKey("research_workspaces.id"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            _UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "status", PACKET_STATUS, nullable=False, server_default="assembling"
        ),
        sa.Column(
            "intelligence_object_ids",
            _UUID_ARRAY,
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "conflict_acknowledged_ids",
            _UUID_ARRAY,
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("ready_at", sa.DateTime(timezone=True)),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_research_packets_status",
        "research_packets",
        ["workspace_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("idx_research_packets_status", table_name="research_packets")
    op.drop_table("research_packets")
    op.drop_index("idx_research_ws_items", table_name="research_workspace_items")
    op.drop_table("research_workspace_items")
    op.drop_table("research_workspaces")
    op.drop_index(
        "idx_intelligence_objects_scoring_version", table_name="intelligence_objects"
    )
    op.drop_index("idx_intelligence_objects_headline", table_name="intelligence_objects")
    op.drop_index("idx_intelligence_objects_score", table_name="intelligence_objects")
    op.drop_index("idx_intelligence_objects_status", table_name="intelligence_objects")
    op.drop_index("idx_intelligence_objects_ws_time", table_name="intelligence_objects")
    op.drop_table("intelligence_objects")
    PACKET_STATUS.drop(op.get_bind(), checkfirst=True)
    RWS_STATUS.drop(op.get_bind(), checkfirst=True)
    INTEL_STATUS.drop(op.get_bind(), checkfirst=True)
