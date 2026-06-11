"""Gmail per-source config + read-only OAuth scope.

ADR-023 enforcement starts here. The scope constant is the ONLY scope this
provider ever requests. Any future Phase 3+ patch that tries to broaden it
will fail the integration test in tests/unit/test_intake_gmail.py.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# READ-ONLY SCOPE. Do not change this. See ADR-023.
# A test asserts this exact string. Adding a second scope requires updating
# the architecture doc + ADR-023 + the test, in that order.
# ---------------------------------------------------------------------------
GMAIL_READONLY_SCOPE: Literal["https://www.googleapis.com/auth/gmail.readonly"] = (
    "https://www.googleapis.com/auth/gmail.readonly"
)
REQUESTED_SCOPES: tuple[str, ...] = (GMAIL_READONLY_SCOPE,)

GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1"
GMAIL_OAUTH_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GMAIL_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"


class GmailSourceConfig(BaseModel):
    """Stored at `intake_sources.config` for kind=gmail."""

    model_config = ConfigDict(extra="ignore")

    # Labels we poll. INBOX is the default; users can pin custom labels in
    # onboarding step 2. Empty list means INBOX only (defensive default).
    labels_watched: list[str] = Field(default_factory=lambda: ["INBOX"])

    # Optional list filters; empty = no filter applied.
    sender_allowlist: list[str] = Field(default_factory=list)
    sender_blocklist: list[str] = Field(default_factory=list)

    # Attachment metadata only — bytes are never fetched in Phase 3.
    include_attachments_metadata: bool = True

    # First-connect historical pull window. Bounded so we don't pull years
    # of email on a brand-new connection.
    max_lookback_days_initial: int = Field(default=14, ge=1, le=90)

    # Polling cadence — overridable per source, capped at vendor-friendly range.
    fetch_interval_minutes: int = Field(default=15, ge=5, le=60)


# ---------------------------------------------------------------------------
# Cursor shape — opaque to the orchestrator, owned by the provider.
# Stored in intake_sources.cursor (jsonb).
# ---------------------------------------------------------------------------
# {
#   "history_id": "12345678",        # last processed historyId
#   "bootstrap_complete": true,      # first historical pull finished
# }
