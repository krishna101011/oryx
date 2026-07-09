"""SMTPEmailProvider — real alert-email delivery over plain SMTP.

Mirrors newsletter.py's _send_smtp (MIMEText plain, smtplib in a thread via
asyncio.to_thread so the event loop never blocks on the socket), with the
provider-layer contract instead of channel errors: auth failures → AUTH,
transport failures → TRANSIENT, unconfigured (no host) → AUTH — always a
ProviderResult, never a raise.
"""
from __future__ import annotations

import asyncio
import smtplib
import uuid
from email.mime.text import MIMEText

from oryx.services.activity.providers.email.base import (
    EmailMessage,
    EmailProvider,
    ProviderErrorKind,
    ProviderResult,
)
from oryx.services.activity.providers.email.rendering import render


class SMTPEmailProvider:
    name = "smtp"

    def __init__(
        self,
        host: str | None,
        *,
        port: int = 587,
        username: str | None = None,
        password: str | None = None,
        from_email: str,
        timeout: float = 30.0,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password or ""
        self._from_email = from_email
        self._timeout = timeout

    async def send(self, message: EmailMessage) -> ProviderResult:
        if not self._host:
            return ProviderResult(
                ok=False,
                provider=self.name,
                error_kind=ProviderErrorKind.AUTH,
                error_message="SMTP_HOST is not configured",
            )
        subject, body = render(message)
        message_id = f"<{uuid.uuid4().hex}@oryx>"

        def _do_send() -> None:
            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = self._from_email
            msg["To"] = message.to
            msg["Message-ID"] = message_id
            with smtplib.SMTP(self._host, self._port, timeout=self._timeout) as server:
                if self._username:
                    server.login(self._username, self._password)
                server.sendmail(self._from_email, [message.to], msg.as_string())

        try:
            await asyncio.to_thread(_do_send)
        except smtplib.SMTPAuthenticationError as exc:
            return ProviderResult(
                ok=False,
                provider=self.name,
                error_kind=ProviderErrorKind.AUTH,
                error_message=f"smtp auth failed: {exc}",
            )
        except (smtplib.SMTPException, OSError) as exc:
            return ProviderResult(
                ok=False,
                provider=self.name,
                error_kind=ProviderErrorKind.TRANSIENT,
                error_message=f"smtp send failed: {exc}",
            )
        return ProviderResult(ok=True, provider=self.name, message_id=message_id)


# Type assertion so mypy verifies the concrete impl satisfies the protocol.
_provider: EmailProvider = SMTPEmailProvider(None, from_email="x@x")
