"""Provider interface contract tests.

Verifies that the LogOnly stubs satisfy the Protocols and emit ProviderResult.
This locks in the contract Phase 3+ vendor implementations must follow.
"""
from __future__ import annotations

import pytest

from anant.services.activity.providers.push.base import PushMessage, PushProvider
from anant.services.activity.providers.push.log_only import LogOnlyPushProvider
from anant.services.auth.providers.email.base import (
    EmailMessage,
    EmailProvider,
    ProviderResult,
)
from anant.services.auth.providers.email.log_only import LogOnlyEmailProvider


def test_log_only_email_satisfies_protocol() -> None:
    p: EmailProvider = LogOnlyEmailProvider()
    assert p.name == "log_only"


def test_log_only_push_satisfies_protocol() -> None:
    p: PushProvider = LogOnlyPushProvider()
    assert p.name == "log_only"


@pytest.mark.asyncio
async def test_log_only_email_send_returns_ok_result() -> None:
    p = LogOnlyEmailProvider()
    res = await p.send(
        EmailMessage(to="x@y.com", template="password_reset", variables={})
    )
    assert isinstance(res, ProviderResult)
    assert res.ok is True
    assert res.provider == "log_only"


@pytest.mark.asyncio
async def test_log_only_push_send_returns_ok_result() -> None:
    p = LogOnlyPushProvider()
    res = await p.send(
        PushMessage(token="t", title="hi", body="hello", data={"k": "v"})
    )
    assert res.ok is True
    assert res.provider == "log_only"
