"""SendGridEmailProvider — real alert-email delivery over the SendGrid v3 API.

Reuses newsletter.py's proven send pattern (services/publishing/channels/
newsletter.py _send_sendgrid): POST /v3/mail/send with a text/plain content
block and a bearer api key; the provider message id comes back in the
X-Message-Id header. The differences are the layer contracts:

  - credentials are PLATFORM-level settings (SENDGRID_API_KEY /
    ALERT_EMAIL_FROM), not a workspace's encrypted publish-target row —
    alert email is ORYX speaking to its own user, not a tenant publishing
    to an audience;
  - failures return ProviderResult(ok=False, error_kind=...) instead of
    raising channel errors — the same never-crash contract as FCM/APNs
    (401/403 → AUTH, 429 → RATE_LIMITED, other 4xx → PERMANENT,
    5xx/network → TRANSIENT), and an unconfigured provider degrades to an
    AUTH failure result.
"""
from __future__ import annotations

import httpx

from oryx.services.activity.providers.email.base import (
    EmailMessage,
    EmailProvider,
    ProviderErrorKind,
    ProviderResult,
)
from oryx.services.activity.providers.email.rendering import render

_SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"


def _kind_for_status(status: int) -> ProviderErrorKind:
    if status in (401, 403):
        return ProviderErrorKind.AUTH
    if status == 429:
        return ProviderErrorKind.RATE_LIMITED
    if 400 <= status < 500:
        return ProviderErrorKind.PERMANENT
    return ProviderErrorKind.TRANSIENT


class SendGridEmailProvider:
    name = "sendgrid"

    def __init__(
        self,
        api_key: str | None,
        *,
        from_email: str,
        from_name: str,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._from_email = from_email
        self._from_name = from_name
        self._timeout = timeout

    async def send(self, message: EmailMessage) -> ProviderResult:
        if not self._api_key:
            return ProviderResult(
                ok=False,
                provider=self.name,
                error_kind=ProviderErrorKind.AUTH,
                error_message="SENDGRID_API_KEY is not configured",
            )
        subject, body = render(message)
        payload = {
            "personalizations": [{"to": [{"email": message.to}]}],
            "from": {"email": self._from_email, "name": self._from_name},
            "subject": subject,
            "content": [{"type": "text/plain", "value": body}],
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "content-type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(_SENDGRID_URL, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            return ProviderResult(
                ok=False,
                provider=self.name,
                error_kind=ProviderErrorKind.TRANSIENT,
                error_message=f"sendgrid unreachable: {exc}",
            )
        if resp.status_code >= 400:
            return ProviderResult(
                ok=False,
                provider=self.name,
                error_kind=_kind_for_status(resp.status_code),
                error_message=f"sendgrid {resp.status_code}: {resp.text[:200]}",
            )
        return ProviderResult(
            ok=True,
            provider=self.name,
            message_id=resp.headers.get("x-message-id"),
        )


# Type assertion so mypy verifies the concrete impl satisfies the protocol.
_provider: EmailProvider = SendGridEmailProvider(None, from_email="x@x", from_name="x")
