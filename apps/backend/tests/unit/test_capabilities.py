"""Role → capability grants. Pure-function unit test of the authorization core."""
from __future__ import annotations

import pytest

from anant.core.dependencies import _role_grants


@pytest.mark.parametrize(
    ("role", "cap", "granted"),
    [
        # owner has wildcard
        ("owner", "anything.at.all", True),
        ("owner", "research.write", True),
        # admin
        ("admin", "research.write", True),
        ("admin", "research.read", True),
        ("admin", "settings.audit", True),
        ("admin", "billing.write", False),
        # editor
        ("editor", "research.write", True),
        ("editor", "research.read", True),
        ("editor", "content.write", True),
        ("editor", "settings.write", False),
        ("editor", "activity.write", False),
        ("editor", "activity.read", True),
        # reader
        ("reader", "research.read", True),
        ("reader", "research.write", False),
        ("reader", "content.write", False),
        ("reader", "activity.read", True),
        # unknown role
        ("ghost", "research.read", False),
    ],
)
def test_role_grants(role: str, cap: str, granted: bool) -> None:
    assert _role_grants(role, cap) is granted


def test_wildcard_does_not_match_root_prefix() -> None:
    # `research.*` should NOT grant a totally different namespace.
    assert _role_grants("admin", "billing.write") is False


def test_wildcard_does_not_match_unrelated_string_prefix() -> None:
    # `research.*` should not match "researchextra.write"
    assert _role_grants("admin", "researchextra.write") is False
