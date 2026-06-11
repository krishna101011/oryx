"""Phase 3 security pass — invariants that must hold at freeze (§17, ADR-023).

Covers the gaps not already exercised elsewhere:
  - No-write-back policy: the Gmail surface is structurally read-only
  - OAuth scope pinning: exactly gmail.readonly, asserted two ways
  - Credential envelope encryption: roundtrip, tenant isolation, tamper,
    version byte

Already covered elsewhere (kept there): SSRF (test_intake_api_pull),
webhook HMAC + replay window (test_intake_webhook), retry classification
(test_intake_retry_classifier), capability boundaries (test_capabilities),
platform-admin gate (test_intake_admin), workspace-scoped queries
(integration suites).
"""
from __future__ import annotations

import uuid

import pytest

from anant.core.security.secrets import (
    decrypt_for_workspace,
    encrypt_for_workspace,
    kms_version_of,
)
from anant.services.intake.providers.gmail import client as gmail_client
from anant.services.intake.providers.gmail.config_schema import REQUESTED_SCOPES

# ---------------------------------------------------------------------------
# ADR-023 — no write-back
# ---------------------------------------------------------------------------

FORBIDDEN_GMAIL_OPERATIONS = (
    "send", "modify", "trash", "untrash", "delete", "insert", "import_",
    "batch_modify", "batch_delete", "create_label", "watch_stop",
)


def test_gmail_client_exposes_no_write_operations() -> None:
    public = [n for n in dir(gmail_client) if not n.startswith("_")]
    for name in public:
        lowered = name.lower()
        for forbidden in FORBIDDEN_GMAIL_OPERATIONS:
            assert forbidden not in lowered, (
                f"gmail client exposes '{name}' — ADR-023 violation"
            )


def test_gmail_scope_is_exactly_readonly() -> None:
    assert REQUESTED_SCOPES == ("https://www.googleapis.com/auth/gmail.readonly",)


def test_auth_url_builder_refuses_tampered_scopes(monkeypatch: pytest.MonkeyPatch) -> None:
    """build_auth_url re-asserts the scope constant at call time."""
    from anant.services.intake.providers.gmail import auth as gmail_auth

    monkeypatch.setattr(
        gmail_auth, "REQUESTED_SCOPES",
        ("https://www.googleapis.com/auth/gmail.modify",),
    )
    with pytest.raises(RuntimeError, match="ADR-023"):
        gmail_auth.build_auth_url(
            client_id="x", redirect_uri="http://localhost/cb", state="s"
        )


# ---------------------------------------------------------------------------
# §11.6 / ADR-021 — credential envelope encryption
# ---------------------------------------------------------------------------

def test_encrypt_decrypt_roundtrip() -> None:
    ws = uuid.uuid4()
    secret = encrypt_for_workspace(b"refresh-token-bytes", workspace_id=ws)
    assert decrypt_for_workspace(secret.blob, workspace_id=ws) == b"refresh-token-bytes"


def test_ciphertext_is_workspace_scoped() -> None:
    # Tenant isolation at the crypto layer: workspace B's derived key
    # cannot open workspace A's ciphertext.
    secret = encrypt_for_workspace(b"top-secret", workspace_id=uuid.uuid4())
    with pytest.raises(Exception):
        decrypt_for_workspace(secret.blob, workspace_id=uuid.uuid4())


def test_tampered_ciphertext_fails_loudly() -> None:
    ws = uuid.uuid4()
    secret = encrypt_for_workspace(b"payload", workspace_id=ws)
    tampered = secret.blob[:-1] + bytes([secret.blob[-1] ^ 0xFF])
    with pytest.raises(Exception):
        decrypt_for_workspace(tampered, workspace_id=ws)


def test_version_byte_is_readable_without_decrypting() -> None:
    secret = encrypt_for_workspace(
        b"x", workspace_id=uuid.uuid4(), kms_key_version=3
    )
    assert kms_version_of(secret.blob) == 3
    assert secret.kms_key_version == 3


def test_short_blob_rejected() -> None:
    with pytest.raises(ValueError):
        decrypt_for_workspace(b"tiny", workspace_id=uuid.uuid4())
