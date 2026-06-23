"""Newsletter channel adapter (§10.2).

config.provider selects the delivery path:
  'sendgrid' → POST https://api.sendgrid.com/v3/mail/send (credentials.api_key)
  'smtp'     → smtplib over credentials.host/port/username/password
Both send a single email; recipients come from config.to. External id is the
provider message id (SendGrid X-Message-Id header / a synthesised id for SMTP).
"""
from __future__ import annotations

import asyncio
import smtplib
import uuid
from email.mime.text import MIMEText
from typing import Any

import httpx

from oryx.services.publishing.channels.base import (
    PermanentChannelError,
    PublishResult,
    TransientChannelError,
)
from oryx.services.publishing.channels.formatting import single_segment
from oryx.services.publishing.channels.http import raise_for_status

_SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"


def _recipients(config: dict[str, Any]) -> list[str]:
    to = config.get("to")
    if isinstance(to, str):
        return [to]
    if isinstance(to, list):
        return [str(x) for x in to]
    return []


class NewsletterChannel:
    channel_type = "email_newsletter"

    def __init__(self, timeout: float = 30.0) -> None:
        self._timeout = timeout

    async def validate_credentials(self, credentials: dict[str, Any]) -> bool:
        # Accept either a SendGrid api_key or a minimally-complete SMTP config.
        if credentials.get("api_key"):
            return True
        return bool(credentials.get("host") and credentials.get("username"))

    async def health_check(self, credentials: dict[str, Any]) -> bool:
        # Liveness without sending: SendGrid key shape / SMTP host presence.
        return await self.validate_credentials(credentials)

    def format_content(self, content: str, max_length: int | None) -> list[str]:
        return single_segment(content, max_length)

    async def publish(
        self,
        content: str,
        draft_title: str,
        credentials: dict[str, Any],
        config: dict[str, Any],
    ) -> PublishResult:
        provider = (config.get("provider") or "sendgrid").lower()
        recipients = _recipients(config)
        if not recipients:
            raise PermanentChannelError(
                f"{self.channel_type}: config.to (recipients) is required"
            )
        if provider == "sendgrid":
            return await self._send_sendgrid(content, draft_title, credentials, recipients)
        if provider == "smtp":
            return await self._send_smtp(content, draft_title, credentials, recipients)
        raise PermanentChannelError(
            f"{self.channel_type}: unknown provider '{provider}'"
        )

    async def _send_sendgrid(
        self, content: str, subject: str, credentials: dict[str, Any], recipients: list[str]
    ) -> PublishResult:
        api_key = credentials.get("api_key")
        from_email = credentials.get("from_email") or "noreply@oryx.local"
        from_name = credentials.get("from_name") or "ORYX"
        body = {
            "personalizations": [{"to": [{"email": r} for r in recipients]}],
            "from": {"email": from_email, "name": from_name},
            "subject": subject,
            "content": [{"type": "text/plain", "value": content}],
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "content-type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(_SENDGRID_URL, headers=headers, json=body)
                raise_for_status(resp, channel=self.channel_type)
        except httpx.HTTPError as exc:
            raise TransientChannelError(
                f"{self.channel_type}: unreachable: {exc}"
            ) from exc
        msg_id = resp.headers.get("x-message-id")
        return PublishResult(external_id=msg_id, external_url=None, status="delivered")

    async def _send_smtp(
        self, content: str, subject: str, credentials: dict[str, Any], recipients: list[str]
    ) -> PublishResult:
        host = str(credentials.get("host") or "")
        port = int(credentials.get("port") or 587)
        username = credentials.get("username")
        password = credentials.get("password") or ""
        from_email = credentials.get("from_email") or username or "noreply@oryx.local"
        message_id = f"<{uuid.uuid4().hex}@oryx>"

        def _do_send() -> None:
            msg = MIMEText(content, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = from_email
            msg["To"] = ", ".join(recipients)
            msg["Message-ID"] = message_id
            try:
                with smtplib.SMTP(host, port, timeout=self._timeout) as server:
                    if username:
                        server.login(username, password)
                    server.sendmail(from_email, recipients, msg.as_string())
            except smtplib.SMTPAuthenticationError as exc:
                raise PermanentChannelError(
                    f"{self.channel_type}: SMTP auth failed: {exc}"
                ) from exc
            except (smtplib.SMTPException, OSError) as exc:
                raise TransientChannelError(
                    f"{self.channel_type}: SMTP send failed: {exc}"
                ) from exc

        await asyncio.to_thread(_do_send)
        return PublishResult(
            external_id=message_id, external_url=None, status="delivered"
        )
