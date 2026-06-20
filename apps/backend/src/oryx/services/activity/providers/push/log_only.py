"""LogOnlyPushProvider — Phase 2 stub. No real push."""
from __future__ import annotations

from oryx.core.logging import get_logger

from .base import ProviderResult, PushMessage, PushProvider

logger = get_logger(__name__)


class LogOnlyPushProvider:
    name = "log_only"

    async def send(self, message: PushMessage) -> ProviderResult:
        logger.info(
            "push.send.log_only",
            extra={"title": message.title, "data_keys": list(message.data.keys())},
        )
        return ProviderResult(ok=True, provider=self.name, message_id="log-only")


_provider: PushProvider = LogOnlyPushProvider()
