"""Tests for environment-specific application configuration safeguards."""

import pytest
from pydantic import ValidationError

from oryx.config import Settings


def test_development_allows_default_jwt_secret() -> None:
    settings = Settings(_env_file=None, environment="dev")
    assert settings.jwt_secret == "dev-only-not-for-prod-please-rotate"


@pytest.mark.parametrize("environment", ["staging", "prod"])
def test_non_dev_rejects_default_jwt_secret(environment: str) -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET must be explicitly configured"):
        Settings(_env_file=None, environment=environment)


@pytest.mark.parametrize("environment", ["staging", "prod"])
@pytest.mark.parametrize("secret", ["short-secret", ""])
def test_non_dev_rejects_short_jwt_secret(environment: str, secret: str) -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET must contain at least 32 bytes"):
        Settings(_env_file=None, environment=environment, jwt_secret=secret)


@pytest.mark.parametrize("environment", ["staging", "prod"])
def test_non_dev_accepts_configured_32_byte_jwt_secret(environment: str) -> None:
    settings = Settings(
        _env_file=None,
        environment=environment,
        jwt_secret="a" * 32,
    )
    assert settings.jwt_secret == "a" * 32
