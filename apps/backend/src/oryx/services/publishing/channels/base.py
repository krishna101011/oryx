"""Channel adapter protocol + shared types (§10.1).

Every channel implements `PublishChannel`. The shape mirrors the Phase 3
IntakeProvider protocol (services/intake/providers/base.py): a structural
Protocol + frozen result dataclass, so each channel folder depends only on
this file and a tiny fake satisfies it in tests without inheritance.

Error taxonomy (§16.3) — the engine branches on the type, not the message:
  PermanentChannelError  bad credentials, account suspended → NEVER retry
  TransientChannelError  rate limit, timeout, 5xx → retry with backoff
Both subclass ChannelError so a catch-all still works.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol, runtime_checkable


@dataclass(frozen=True)
class PublishResult:
    """Outcome of a single successful adapter.publish() call.

    `status` is always 'delivered' on the return path — a failed delivery is
    signalled by raising a ChannelError, never by returning status='failed'.
    The 'failed' literal exists so callers can construct a uniform record shape.
    """

    external_id: str | None
    external_url: str | None
    status: Literal["delivered", "failed"]


class ChannelError(Exception):
    """Base for all channel delivery failures."""


class PermanentChannelError(ChannelError):
    """Unrecoverable — bad credentials, suspended account, malformed config.
    The engine marks the publication 'failed' immediately and never retries."""


class TransientChannelError(ChannelError):
    """Recoverable — rate limit, timeout, 5xx. The engine leaves the
    publication 'pending' for the outbox drainer to retry, up to 5 attempts."""


@runtime_checkable
class PublishChannel(Protocol):
    """Structural contract every channel adapter satisfies."""

    channel_type: str

    async def validate_credentials(self, credentials: dict[str, Any]) -> bool:
        """True if the credentials are well-formed and accepted by the channel.
        Called before a target is saved (create_target) — a False result is a
        400 and the target is not persisted."""
        ...

    async def health_check(self, credentials: dict[str, Any]) -> bool:
        """Liveness probe used by POST /targets/{id}/health-check."""
        ...

    async def publish(
        self,
        content: str,
        draft_title: str,
        credentials: dict[str, Any],
        config: dict[str, Any],
    ) -> PublishResult:
        """Deliver `content` to the channel. Raises PermanentChannelError /
        TransientChannelError on failure; returns a PublishResult on success."""
        ...

    def format_content(self, content: str, max_length: int | None) -> list[str]:
        """Split/shape content for the channel. Returns one or more segments
        (e.g. a tweet thread). `max_length` None means no per-segment cap."""
        ...
