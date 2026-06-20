"""LogOnlyEmailProvider — Phase 2 stub. No real send."""
from __future__ import annotations

from oryx.core.logging import get_logger

from .base import EmailMessage, EmailProvider, ProviderResult

logger = get_logger(__name__)


class LogOnlyEmailProvider:
    name = "log_only"

    async def send(self, message: EmailMessage) -> ProviderResult:
        logger.info(
            "email.send.log_only",
            extra={"template": message.template, "to_domain": message.to.split("@")[-1]},
        )
        return ProviderResult(ok=True, provider=self.name, message_id="log-only")


# Type assertion so mypy verifies the concrete impl satisfies the protocol.
_provider: EmailProvider = LogOnlyEmailProvider()
