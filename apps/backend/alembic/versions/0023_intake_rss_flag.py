"""Enable ff_intake_rss.

Phase 3 shipped the entire RSS intake path the flag stands for: RssProvider
(conditional-GET client with a 5 MiB body cap and typed error taxonomy, parser,
mapper, sync loop with etag/last-modified cursor and CR-10 permanent-redirect
persistence), create-time config validation in the intake router, and the
IntakeScheduler → SourceSyncRunner execution path with per-item ingest
transactions, two-tier fingerprint dedupe, retry classification, and the §10.3
circuit breaker — all covered by test_intake_rss_provider / scheduler /
fingerprint / normalizer suites. Yet the flag was never flipped after the wave
froze, so Manage Sources has offered nothing to add and Phase 3 has never seen
real data.

Same reasoning standard as 0016 (ff_automation), 0018 (ff_push_delivery),
0020 (ff_analytics) and 0022 (ff_email_delivery): safe to flip because
(a) the flag gates ONLY a client surface — the "Add an RSS feed" card on
SourceManagementScreen; every backend endpoint it leads to (POST/GET
/intake/sources, the scheduler) is already live, capability-gated
(intake.write), and NOT flag-gated, so flipping changes no server behavior
and opens no new server surface; (b) the revealed flow is bounded end to end:
pydantic HttpUrl + provider validation at create time, outbound-only
conditional GET with timeout and size cap at sync time, per-item transactions
and provider-key + fingerprint dedupe at write time, and failure routing
through the retry classifier into backoff and the 10-failure circuit breaker —
a bad feed URL degrades that one source, nothing else; (c) worst case is the
status quo: a validation error at create, or sync_failed audit rows and an
unhealthy source card.

Known gap, recorded not hidden: the RSS fetcher has no SSRF guard (api_pull's
providers/api_pull/safety.py deliberately built one for the same
user-controlled-URL threat). That exposure lives on the ALREADY-live,
non-flag-gated create endpoint, so this flip neither creates nor widens it;
porting the guard to RSS is tracked as follow-up hardening.

Data-only migration; no schema change.

Revision ID: 0023_intake_rss_flag
Revises: 0022_email_delivery_flag
Create Date: 2026-07-11
"""
from __future__ import annotations

from alembic import op

revision = "0023_intake_rss_flag"
down_revision = "0022_email_delivery_flag"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE feature_flags SET default_enabled = true WHERE key = 'ff_intake_rss'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE feature_flags SET default_enabled = false WHERE key = 'ff_intake_rss'"
    )
