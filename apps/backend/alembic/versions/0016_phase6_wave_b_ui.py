"""Phase 6 Wave B (UI) — enable ff_automation.

The Automation Hub (Rules + Log tabs) ships this wave and depends only on
Wave A/B functionality already live: alert_preferences (read), automation_log
and digest_runs (read). Nothing it exposes requires Wave C push delivery, so
the flag flips ON globally. ff_push_delivery stays at its seeded default
(off) until Wave C.

Data-only migration; no schema change.

Revision ID: 0016_phase6_wave_b_ui
Revises: 0015_phase6_wave_b
Create Date: 2026-07-07
"""
from __future__ import annotations

from alembic import op

revision = "0016_phase6_wave_b_ui"
down_revision = "0015_phase6_wave_b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE feature_flags SET default_enabled = true WHERE key = 'ff_automation'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE feature_flags SET default_enabled = false WHERE key = 'ff_automation'"
    )
