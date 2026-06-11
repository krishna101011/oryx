"""HMAC signing + verification for inbound webhooks.

Signature scheme (locked in Phase 3 §6.2):
    signature = "hmac-sha256=" + hex(hmac_sha256(secret, f"{timestamp}.{raw_body}"))

The verifier:
  - parses the signature header tolerantly (accepts bare hex or prefixed)
  - reconstructs the signing string deterministically
  - constant-time compares
  - validates the timestamp falls inside the replay window

The router is the only caller of `verify_request()`. Per-source secret
generation happens at connect time; `generate_secret()` returns a value the
user sees ONCE, then we store its sha256 hash. The verifier never compares
against the hash — it operates over the live secret value loaded from
intake_credentials.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets as py_secrets
import time
from dataclasses import dataclass
from enum import Enum

from anant.services.intake.providers.errors import (
    ProviderError,
    ProviderErrorKind,
)
from anant.services.intake.providers.webhook.config_schema import (
    REPLAY_WINDOW_SECONDS,
)

# Display-once secret format. 32 random bytes → 43 base64url chars.
SECRET_BYTES = 32


class WebhookAuthFailureReason(str, Enum):
    MISSING_HEADER = "missing_header"
    BAD_TIMESTAMP = "bad_timestamp"
    OUTSIDE_REPLAY_WINDOW = "outside_replay_window"
    BAD_SIGNATURE = "bad_signature"


@dataclass(frozen=True)
class WebhookVerified:
    """Returned by verify_request() on success — caller uses idempotency_key
    to dedupe against webhook_idempotency_keys."""

    timestamp: int


def generate_secret() -> str:
    """Per-source webhook secret. Shown to the user once at connect time."""
    return py_secrets.token_urlsafe(SECRET_BYTES)


def hash_secret_for_audit(secret: str) -> str:
    """SHA-256 hex of the secret. Stored separately if we ever want to audit
    "was this secret value rotated?" without keeping the secret around."""
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def sign_request(*, secret: str, timestamp: int, body: bytes) -> str:
    """Build the signature header value. Used by senders + tests."""
    payload = f"{timestamp}.".encode("ascii") + body
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return f"hmac-sha256={digest}"


def verify_request(
    *,
    secrets: list[str],
    signature_header: str | None,
    timestamp_header: str | None,
    body: bytes,
    now: int | None = None,
) -> WebhookVerified:
    """Verify a request against one or more accepted secrets.

    `secrets` is a list to support the 24h rotation grace window — Phase 3
    pushes both the new and the previous secret into this list at connect
    time. If ANY secret produces a matching signature we accept.

    Raises ProviderError(PERMANENT) on any failure with a discriminant in
    `details.reason` so the router can return the right wire shape.
    """
    if not signature_header or not timestamp_header:
        raise ProviderError(
            kind=ProviderErrorKind.PERMANENT,
            message="Missing signature or timestamp header",
        )
    try:
        ts = int(timestamp_header)
    except ValueError as e:
        raise ProviderError(
            kind=ProviderErrorKind.PERMANENT,
            message="Timestamp header is not an integer",
        ) from e

    current = now if now is not None else int(time.time())
    if abs(current - ts) > REPLAY_WINDOW_SECONDS:
        raise ProviderError(
            kind=ProviderErrorKind.PERMANENT,
            message="Timestamp outside replay window",
        )

    presented = _strip_scheme(signature_header)
    for s in secrets:
        expected = sign_request(secret=s, timestamp=ts, body=body)
        expected_hex = _strip_scheme(expected)
        if hmac.compare_digest(presented, expected_hex):
            return WebhookVerified(timestamp=ts)
    raise ProviderError(
        kind=ProviderErrorKind.PERMANENT,
        message="Signature does not match any accepted secret",
    )


def _strip_scheme(header: str) -> str:
    s = header.strip()
    if "=" in s and s.lower().startswith("hmac-sha256="):
        return s.split("=", 1)[1].strip()
    return s
