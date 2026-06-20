"""PushProvider interface.

Phase 2 ships LogOnlyPushProvider. Phase 6 introduces FCM / APNs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from oryx.services.auth.providers.email.base import ProviderErrorKind, ProviderResult


@dataclass(frozen=True)
class PushMessage:
    token: str
    title: str
    body: str
    data: dict[str, Any]


class PushProvider(Protocol):
    name: str

    async def send(self, message: PushMessage) -> ProviderResult: ...


# Re-export so downstream modules can import a single names from this package.
__all__ = ["ProviderErrorKind", "ProviderResult", "PushMessage", "PushProvider"]
