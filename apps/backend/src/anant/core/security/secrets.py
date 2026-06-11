"""Envelope encryption for workspace-scoped secrets.

Phase 3 uses this to protect `intake_credentials.encrypted_token` and
`encrypted_refresh_token`. The mechanism is HKDF over a master key
(`INTAKE_KMS_KEY` in Settings) plus a workspace_id-derived label, with
AES-GCM as the AEAD primitive.

Why envelope encryption per workspace:
- A workspace export / hard-delete can decrypt and re-encrypt without
  touching other tenants' ciphertexts.
- Rotating the master key is documented in docs/PHASE_3_ARCHITECTURE.md
  Appendix C; the `kms_key_version` column on intake_credentials lets the
  rotator skip already-migrated rows.

Why AES-GCM:
- Authenticated. Tampering produces decryption failure, not silent corruption.
- Standard library support; no extra dependency surface.

Storage shape (bytes):
    [ kms_key_version: 1 byte ]
    [ nonce: 12 bytes ]
    [ ciphertext+tag: variable ]
"""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from anant.config import get_settings

_NONCE_LEN = 12
_KEY_LEN = 32  # AES-256


@dataclass(frozen=True)
class EncryptedSecret:
    blob: bytes
    kms_key_version: int

    def to_bytes(self) -> bytes:
        return self.blob


def _master_key() -> bytes:
    settings = get_settings()
    raw = getattr(settings, "intake_kms_key", None)
    if not raw:
        # Phase 3 implementations must override; dev gets a deterministic key.
        raw = "dev-only-intake-kms-key-32-bytes!"
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    if len(raw) < 16:
        raise RuntimeError("INTAKE_KMS_KEY too short")
    return raw


def _derive_workspace_key(workspace_id: uuid.UUID, version: int) -> bytes:
    """HKDF-derive a per-workspace, per-version AES-256 key."""
    info = f"intake/v{version}/workspace/{workspace_id}".encode()
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=_KEY_LEN,
        salt=None,
        info=info,
    )
    return hkdf.derive(_master_key())


def encrypt_for_workspace(
    plaintext: bytes, *, workspace_id: uuid.UUID, kms_key_version: int = 1
) -> EncryptedSecret:
    """Encrypt with the workspace-derived key. Output begins with version byte."""
    key = _derive_workspace_key(workspace_id, kms_key_version)
    nonce = os.urandom(_NONCE_LEN)
    ct = AESGCM(key).encrypt(nonce, plaintext, None)
    blob = bytes([kms_key_version]) + nonce + ct
    return EncryptedSecret(blob=blob, kms_key_version=kms_key_version)


def decrypt_for_workspace(blob: bytes, *, workspace_id: uuid.UUID) -> bytes:
    """Decrypt, reading the leading version byte."""
    if len(blob) < 1 + _NONCE_LEN + 16:
        raise ValueError("Ciphertext too short to be valid")
    version = blob[0]
    nonce = blob[1 : 1 + _NONCE_LEN]
    ct = blob[1 + _NONCE_LEN :]
    key = _derive_workspace_key(workspace_id, version)
    return AESGCM(key).decrypt(nonce, ct, None)


def kms_version_of(blob: bytes) -> int:
    if not blob:
        raise ValueError("Empty ciphertext")
    return blob[0]
