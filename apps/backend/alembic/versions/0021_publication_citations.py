"""Transparency — publication_citations provenance snapshot.

Creates publication_citations: one row per (publication, cited intelligence
object), holding the object's headline, epistemic_type, confidence_score and
scoring_version AS THEY WERE when the publication row was created. The engine
writes these in the SAME transaction as the pending publication insert
(ON CONFLICT DO NOTHING on the composite PK keeps retries idempotent), so a
publication can never exist without its snapshot and a later re-score can
never rewrite what a published piece claimed at the time.

Boundary note: intelligence-object level only — deliberately NO claim or
evidence columns/FKs, matching the publishing layer's existing public
boundary (services/publishing/citations.py: "never raw claims/evidence").

Reuses the existing epistemic_type enum (create_type=False).

Revision ID: 0021_publication_citations
Revises: 0020_phase7_wave_b_flag
Create Date: 2026-07-09
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0021_publication_citations"
down_revision = "0020_phase7_wave_b_flag"
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
        "publication_citations",
        sa.Column(
            "publication_id",
            _UUID,
            sa.ForeignKey("publications.id", ondelete="CASCADE"),
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
    op.drop_table("publication_citations")
