"""Webhook per-source config.

The generic_json mapper extracts fields from the inbound JSON body by
dotted path. A vendor-specific provider (Phase 3.x) can override the
mapper entirely; this config is the contract for the default provider.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class WebhookFieldMapping(BaseModel):
    """Dotted-path selectors over the inbound JSON body."""

    model_config = ConfigDict(extra="ignore")

    # Required: how to uniquely identify the item upstream
    external_id: str = "id"
    received_at: str | None = "created_at"
    sender: str | None = "from"
    subject: str | None = "subject"
    body_text: str | None = "body"
    body_html: str | None = None
    primary_link: str | None = "url"


class WebhookSourceConfig(BaseModel):
    """Stored at `intake_sources.config` for kind=webhook."""

    model_config = ConfigDict(extra="ignore")

    mapping: WebhookFieldMapping = Field(default_factory=WebhookFieldMapping)
    # The current HMAC secret is held in intake_credentials (not here — secrets
    # never live in config). A previous secret may be carried in the credential
    # row for a 24h rotation grace window.
    secret_rotation_grace_seconds: int = Field(default=86400, ge=0, le=86400 * 7)


# Inbound-header names. Locked here so router + verifier share them.
HEADER_SIGNATURE = "X-Anant-Signature"
HEADER_TIMESTAMP = "X-Anant-Timestamp"
HEADER_IDEMPOTENCY_KEY = "X-Anant-Idempotency-Key"

# Body cap. The router rejects anything larger at the edge.
MAX_BODY_BYTES = 256 * 1024

# Replay window. ±300s by spec §6.2.
REPLAY_WINDOW_SECONDS = 300
