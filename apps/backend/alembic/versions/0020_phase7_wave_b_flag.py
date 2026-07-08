"""Phase 7 Wave B — enable ff_analytics.

Wave B ships the full read path the flag gates: GET /v1/analytics/rollups +
GET /v1/analytics/publishing (both read-only over Wave A's already-correct
rollup table plus the one sanctioned time-to-publish query) and the Analytics
screen (Overview KPIs/charts, research funnel, §3.4-limited publishing view).

Same reasoning standard as 0016 (ff_automation) and 0018 (ff_push_delivery):
everything the flag exposes client-side is shipped and tested end to end —
and Phase 7 is purely observational by design (frozen doc §1.2: not
load-bearing for any other phase), so the worst case a user can reach is the
designed-and-tested "still gathering data" state, which is the honest current
state of every workspace (the rollup table only began filling when Wave A
shipped). Flipping the flag cannot write anything or affect any other
phase's correctness.

Data-only migration; no schema change.

Revision ID: 0020_phase7_wave_b_flag
Revises: 0019_phase7_wave_a_analytics
Create Date: 2026-07-08
"""
from __future__ import annotations

from alembic import op

revision = "0020_phase7_wave_b_flag"
down_revision = "0019_phase7_wave_a_analytics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE feature_flags SET default_enabled = true WHERE key = 'ff_analytics'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE feature_flags SET default_enabled = false WHERE key = 'ff_analytics'"
    )
