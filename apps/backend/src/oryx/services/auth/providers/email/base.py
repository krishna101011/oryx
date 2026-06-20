"""EmailProvider interface.

The email provider is the seam where vendor SDKs are isolated.
Phase 2 ships LogOnlyEmailProvider only; Phase 6 introduces real delivery.

Service code depends on this interface, never on a concrete vendor module.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class ProviderErrorKind(str, Enum):
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    RATE_LIMITED = "rate_limited"
    AUTH = "auth"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ProviderResult:
    ok: bool
    provider: str
    message_id: str | None = None
    error_kind: ProviderErrorKind | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class EmailMessage:
    to: str
    template: str  # e.g. 'password_reset', 'welcome'
    variables: dict[str, str]


class EmailProvider(Protocol):
    name: str

    async def send(self, message: EmailMessage) -> ProviderResult: ...
