"""SendGrid/SMTP alert-email providers + the EMAIL_PROVIDER switch (unit, no DB).

Same standard as test_push_providers.py: the real implementations exercised
through a faked transport layer, the error taxonomy (401/403 → AUTH, 429 →
RATE_LIMITED, other 4xx → PERMANENT, 5xx/network → TRANSIENT), and the
factory's env gating — log_only by default, an unconfigured real provider
degrading to an AUTH failure result instead of raising.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest

from oryx.services.activity.providers.email.base import (
    EmailMessage,
    ProviderErrorKind,
)
from oryx.services.activity.providers.email.rendering import render
from oryx.services.activity.providers.email.sendgrid import SendGridEmailProvider


def _message() -> EmailMessage:
    return EmailMessage(
        to="user@oryx.test",
        template="alert",
        variables={
            "title": "Conflict detected",
            "category": "verification",
            "severity": "warning",
            "event_type": "verification.conflict.detected",
        },
    )


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def test_alert_template_renders_subject_and_plain_body() -> None:
    subject, body = render(_message())
    assert subject == "ORYX alert: Conflict detected"
    assert "Category: verification" in body
    assert "Severity: warning" in body
    assert "verification.conflict.detected" in body


def test_password_reset_template_renders_token_and_expiry() -> None:
    subject, body = render(
        EmailMessage(
            to="u@x",
            template="password_reset",
            variables={"reset_token": "tok-abc123", "expires_minutes": "30"},
        )
    )
    assert subject == "ORYX password reset"
    assert "tok-abc123" in body
    assert "30 minutes" in body


def test_unknown_template_falls_back_instead_of_raising() -> None:
    subject, body = render(
        EmailMessage(to="u@x", template="never_registered", variables={"k": "v"})
    )
    assert "never_registered" in subject
    assert "k: v" in body


# --------------------------------------------------------------------------- #
# SendGrid — faked httpx transport (newsletter.py's proven request shape)
# --------------------------------------------------------------------------- #
def _sendgrid(api_key: str | None = "sg-key") -> SendGridEmailProvider:
    return SendGridEmailProvider(
        api_key, from_email="alerts@oryx.local", from_name="ORYX Alerts"
    )


def _transport(status: int, headers: dict | None = None) -> httpx.MockTransport:
    return httpx.MockTransport(
        lambda request: httpx.Response(status, headers=headers or {}, text="resp")
    )


def _patched_client(transport: httpx.MockTransport, seen: dict):
    real_init = httpx.AsyncClient.__init__

    def init(self, *args, **kwargs):  # force the mock transport into the client
        kwargs["transport"] = transport
        real_init(self, *args, **kwargs)
        seen["client"] = self

    return patch.object(httpx.AsyncClient, "__init__", init)


@pytest.mark.asyncio
async def test_sendgrid_send_success_returns_message_id() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        import json

        captured["body"] = json.loads(request.content)
        return httpx.Response(202, headers={"x-message-id": "sg-msg-1"})

    with _patched_client(httpx.MockTransport(handler), {}):
        result = await _sendgrid().send(_message())

    assert result.ok is True
    assert result.message_id == "sg-msg-1"
    assert captured["url"] == "https://api.sendgrid.com/v3/mail/send"
    assert captured["auth"] == "Bearer sg-key"
    body = captured["body"]
    assert body["personalizations"] == [{"to": [{"email": "user@oryx.test"}]}]
    assert body["from"] == {"email": "alerts@oryx.local", "name": "ORYX Alerts"}
    assert body["content"][0]["type"] == "text/plain"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "kind"),
    [
        (401, ProviderErrorKind.AUTH),
        (403, ProviderErrorKind.AUTH),
        (429, ProviderErrorKind.RATE_LIMITED),
        (400, ProviderErrorKind.PERMANENT),
        (500, ProviderErrorKind.TRANSIENT),
    ],
)
async def test_sendgrid_error_taxonomy(status: int, kind: ProviderErrorKind) -> None:
    with _patched_client(_transport(status), {}):
        result = await _sendgrid().send(_message())
    assert result.ok is False
    assert result.error_kind == kind


@pytest.mark.asyncio
async def test_sendgrid_unconfigured_degrades_to_auth_failure() -> None:
    result = await _sendgrid(api_key=None).send(_message())
    assert result.ok is False
    assert result.error_kind == ProviderErrorKind.AUTH


# --------------------------------------------------------------------------- #
# SMTP — unconfigured guard (the smtplib path itself is newsletter-proven)
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_smtp_unconfigured_degrades_to_auth_failure() -> None:
    from oryx.services.activity.providers.email.smtp import SMTPEmailProvider

    result = await SMTPEmailProvider(None, from_email="alerts@oryx.local").send(
        _message()
    )
    assert result.ok is False
    assert result.error_kind == ProviderErrorKind.AUTH


# --------------------------------------------------------------------------- #
# Factory — the EMAIL_PROVIDER switch
# --------------------------------------------------------------------------- #
def _settings(**over):
    base = {
        "email_provider": "log_only",
        "sendgrid_api_key": None,
        "alert_email_from": "alerts@oryx.local",
        "alert_email_from_name": "ORYX Alerts",
        "smtp_host": None,
        "smtp_port": 587,
        "smtp_username": None,
        "smtp_password": None,
    }
    base.update(over)
    return SimpleNamespace(**base)


def test_factory_defaults_to_log_only() -> None:
    from oryx.services.activity.providers.email.factory import get_email_provider
    from oryx.services.auth.providers.email.log_only import LogOnlyEmailProvider

    assert isinstance(get_email_provider(_settings()), LogOnlyEmailProvider)


def test_factory_selects_sendgrid_and_smtp() -> None:
    from oryx.services.activity.providers.email.factory import get_email_provider
    from oryx.services.activity.providers.email.smtp import SMTPEmailProvider

    assert isinstance(
        get_email_provider(_settings(email_provider="sendgrid", sendgrid_api_key="k")),
        SendGridEmailProvider,
    )
    assert isinstance(
        get_email_provider(_settings(email_provider="smtp", smtp_host="mail.local")),
        SMTPEmailProvider,
    )


def test_factory_unknown_value_falls_back_to_log_only() -> None:
    from oryx.services.activity.providers.email.factory import get_email_provider
    from oryx.services.auth.providers.email.log_only import LogOnlyEmailProvider

    assert isinstance(
        get_email_provider(_settings(email_provider="carrier_pigeon")),
        LogOnlyEmailProvider,
    )
