"""Password hashing + policy + refresh token helpers.

These are the most security-critical pieces of Phase 2. Any regression here
becomes a credential compromise vector.
"""
from __future__ import annotations

import hashlib

import pytest

from anant.core.errors import AuthPasswordWeakError
from anant.core.security.passwords import (
    PasswordPolicy,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    needs_rehash,
    validate_password,
    verify_password,
)

# ---- validate_password ----

def test_password_too_short_rejected() -> None:
    with pytest.raises(AuthPasswordWeakError) as exc:
        validate_password("short1A", PasswordPolicy(min_length=10))
    assert exc.value.details.get("reason") == "too_short"


def test_password_missing_letter_rejected() -> None:
    with pytest.raises(AuthPasswordWeakError) as exc:
        validate_password("1234567890", PasswordPolicy(min_length=10))
    assert exc.value.details.get("reason") == "no_letter"


def test_password_missing_digit_rejected() -> None:
    with pytest.raises(AuthPasswordWeakError) as exc:
        validate_password("alphabeticalonly", PasswordPolicy(min_length=10))
    assert exc.value.details.get("reason") == "no_digit"


def test_password_valid_passes() -> None:
    validate_password("StrongPass123", PasswordPolicy(min_length=10))


# ---- hash / verify ----

def test_hash_and_verify_round_trips() -> None:
    h = hash_password("StrongPass123")
    assert verify_password(h, "StrongPass123") is True


def test_hash_is_not_plaintext() -> None:
    h = hash_password("StrongPass123")
    assert "StrongPass123" not in h
    assert h.startswith("$argon2id$")


def test_verify_rejects_wrong_password() -> None:
    h = hash_password("StrongPass123")
    assert verify_password(h, "WrongPass456") is False


def test_verify_rejects_malformed_hash_without_raising() -> None:
    # Important: never leak which kind of failure happened to callers.
    assert verify_password("not-a-valid-hash", "anything") is False


def test_needs_rehash_false_for_fresh_hash() -> None:
    h = hash_password("StrongPass123")
    assert needs_rehash(h) is False


def test_needs_rehash_true_for_invalid_hash() -> None:
    assert needs_rehash("garbage") is True


# ---- refresh tokens ----

def test_generate_refresh_token_high_entropy() -> None:
    samples = {generate_refresh_token() for _ in range(50)}
    assert len(samples) == 50  # no collisions


def test_generate_refresh_token_length_reasonable() -> None:
    token = generate_refresh_token()
    # token_urlsafe(48) → ~64 chars.
    assert len(token) >= 60


def test_hash_refresh_token_is_sha256_hex() -> None:
    token = "fixed-token-for-test"
    expected = hashlib.sha256(token.encode("utf-8")).hexdigest()
    assert hash_refresh_token(token) == expected


def test_hash_refresh_token_deterministic() -> None:
    token = "abc123"
    assert hash_refresh_token(token) == hash_refresh_token(token)


def test_hash_refresh_token_different_for_different_input() -> None:
    assert hash_refresh_token("a") != hash_refresh_token("b")
