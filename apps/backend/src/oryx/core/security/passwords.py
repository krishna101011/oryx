"""Password hashing and policy.

Argon2id with sensible defaults. Policy is enforced server-side authoritatively.
The Argon2 hash is self-describing (parameters embedded), so changing
parameters later does not require re-hashing existing passwords.
"""
from __future__ import annotations

import hashlib
import re
import secrets
from dataclasses import dataclass

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerifyMismatchError

from oryx.config import get_settings
from oryx.core.errors import AuthPasswordWeakError

# OWASP-recommended Argon2id parameters (time-memory tradeoff: ~50ms on modern hw)
_HASHER = PasswordHasher(
    time_cost=3,
    memory_cost=64 * 1024,  # 64 MiB
    parallelism=2,
    hash_len=32,
    salt_len=16,
)


@dataclass(frozen=True)
class PasswordPolicy:
    min_length: int
    require_letter: bool = True
    require_digit: bool = True


def get_policy() -> PasswordPolicy:
    return PasswordPolicy(min_length=get_settings().password_min_length)


def validate_password(password: str, policy: PasswordPolicy | None = None) -> None:
    """Raise AuthPasswordWeakError if the password fails policy."""
    p = policy or get_policy()
    if len(password) < p.min_length:
        raise AuthPasswordWeakError(
            details={"reason": "too_short", "min_length": p.min_length}
        )
    if p.require_letter and not re.search(r"[A-Za-z]", password):
        raise AuthPasswordWeakError(details={"reason": "no_letter"})
    if p.require_digit and not re.search(r"\d", password):
        raise AuthPasswordWeakError(details={"reason": "no_digit"})


def hash_password(password: str) -> str:
    """Hash a plaintext password. Caller MUST call validate_password first."""
    return _HASHER.hash(password)


def verify_password(stored_hash: str, password: str) -> bool:
    """Constant-time-ish verify. Returns False on mismatch; raises on malformed hash."""
    try:
        return _HASHER.verify(stored_hash, password)
    except VerifyMismatchError:
        return False
    except InvalidHash:
        # Treat malformed stored hash as failed verification (don't leak details).
        return False


def needs_rehash(stored_hash: str) -> bool:
    """True if the hash uses outdated parameters; caller should rehash on next login."""
    try:
        return _HASHER.check_needs_rehash(stored_hash)
    except InvalidHash:
        return True


def password_fingerprint(stored_hash: str) -> str:
    """Short stable digest of a password HASH (never the plaintext). Embedded
    in password-reset tokens so a password change invalidates them."""
    return hashlib.sha256(stored_hash.encode("utf-8")).hexdigest()[:16]


def generate_refresh_token() -> str:
    """High-entropy opaque token. Stored as SHA-256 hash in the DB."""
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    """SHA-256 hex digest. Used as the unique key in sessions.refresh_token_hash."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
