"""Phase 6 Wave C — enable ff_push_delivery.

Wave C ships the full push path: client raw-token registration (guarded so
Expo Go / web never register an unusable token), quiet-hours evaluation, real
FCM/APNs providers behind the PUSH_PROVIDER switch (default log_only), and the
dispatcher's decoupled push step. The flag flips ON globally — same reasoning
standard as 0016's ff_automation flip: everything the flag exposes client-side
(registration + the quiet-hours control) is shipped and tested, and server-side
delivery stays log-only until PUSH_PROVIDER=real is deliberately configured
with credentials, so enabling the flag cannot page a single real device by
accident.

Data-only migration; no schema change.

Revision ID: 0018_phase6_wave_c_flag
Revises: 0017_phase6_wave_c_channel
Create Date: 2026-07-07
"""
from __future__ import annotations

from alembic import op

revision = "0018_phase6_wave_c_flag"
down_revision = "0017_phase6_wave_c_channel"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE feature_flags SET default_enabled = true WHERE key = 'ff_push_delivery'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE feature_flags SET default_enabled = false WHERE key = 'ff_push_delivery'"
    )
