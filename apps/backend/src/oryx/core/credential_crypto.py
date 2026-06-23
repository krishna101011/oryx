"""AES-256-GCM encryption for publish-target channel credentials (§10.3 / ADR-041).

Why a separate module from core/security/secrets.py:
- Phase 3's secrets.py does *workspace-derived envelope* encryption (HKDF per
  workspace) for intake tokens. Publish targets use a single global publish key
  with the exact contract the Phase 5 architecture froze:
      encrypt_credentials(dict) -> (ciphertext, iv)
  Reusing the workspace-envelope shape here would mean changing that contract.
  We deliberately follow the same AESGCM primitive from the `cryptography`
  library (already a dependency) so there is one AEAD implementation choice
  across the codebase.

Storage: `ciphertext` (with the GCM tag appended by AESGCM) and `iv` (12 random
bytes per call) go into publish_targets.credentials / credentials_iv (BYTEA).

The plaintext is a JSON-serialisable dict of channel credential fields. It MUST
never reach a log line, an event payload, or any API response (write-only).
"""
from __future__ import annotations

import base64
import json
import os
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from oryx.config import get_settings

_IV_LEN = 12  # 96-bit nonce — the GCM standard.
_KEY_LEN = 32  # AES-256.

# Obvious dev-only fallback. base64 of a clearly-labelled 32-byte string. The
# real key arrives via ORYX_PUBLISH_KEY; this exists only so the unit suite and
# local dev run without a configured secret. NEVER ships to staging/prod.
_DEV_PLACEHOLDER_KEY = b"DEV-ONLY-PLACEHOLDER-PUBLISH-KEY"  # exactly 32 bytes


def _load_key() -> bytes:
    """Resolve the 32-byte AES key from settings.oryx_publish_key.

    The env value is base64-encoded (so a raw binary key survives .env). If it
    is absent we fall back to the obvious dev placeholder. A configured value
    that does not decode to exactly 32 bytes is a hard error — we never silently
    pad or truncate a key.
    """
    raw = getattr(get_settings(), "oryx_publish_key", None)
    if not raw:
        return _DEV_PLACEHOLDER_KEY
    try:
        key = base64.b64decode(raw, validate=True)
    except Exception as exc:  # malformed base64
        raise RuntimeError(
            "ORYX_PUBLISH_KEY must be base64-encoded 32 bytes"
        ) from exc
    if len(key) != _KEY_LEN:
        raise RuntimeError(
            f"ORYX_PUBLISH_KEY must decode to {_KEY_LEN} bytes, got {len(key)}"
        )
    return key


def encrypt_credentials(plaintext: dict[str, Any]) -> tuple[bytes, bytes]:
    """AES-256-GCM encrypt a credential dict. Returns (ciphertext, iv).

    A fresh random 12-byte IV is generated per call (GCM is catastrophically
    unsafe under nonce reuse). The authentication tag is appended to the
    ciphertext by AESGCM and verified on decrypt.
    """
    key = _load_key()
    iv = os.urandom(_IV_LEN)
    data = json.dumps(plaintext, separators=(",", ":")).encode("utf-8")
    ciphertext = AESGCM(key).encrypt(iv, data, None)
    return ciphertext, iv


def decrypt_credentials(ciphertext: bytes, iv: bytes) -> dict[str, Any]:
    """Inverse of encrypt_credentials. Raises on tamper (GCM tag mismatch)."""
    key = _load_key()
    data = AESGCM(key).decrypt(iv, ciphertext, None)
    result: dict[str, Any] = json.loads(data.decode("utf-8"))
    return result
