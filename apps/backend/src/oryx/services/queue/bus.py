"""Event bus interface + in-process implementation (Stage B drainer side).

The `EventBus` protocol is stable across the three stages defined in
ADR-014; Phase 3 ships the in-process implementation; Phase 6 will swap to
Redis Streams / NATS without touching service code.

Subscribers are async callables. They MUST be idempotent — at-least-once
delivery is the contract.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from oryx.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class DomainEvent:
    id: str
    name: str
    version: int
    occurred_at: datetime
    emitted_at: datetime
    workspace_id: str | None
    actor_kind: str
    actor_id: str | None
    correlation_id: str
    causation_id: str | None
    payload: dict[str, Any]


EventHandler = Callable[[DomainEvent], Awaitable[None]]


class EventBus(Protocol):
    async def publish(self, event: DomainEvent) -> None: ...

    def subscribe(self, name: str, handler: EventHandler) -> None: ...


class InProcessBus:
    """Simple fan-out bus. One process. No persistence (the outbox handles that)."""

    def __init__(self) -> None:
        self._subs: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, name: str, handler: EventHandler) -> None:
        self._subs[name].append(handler)

    async def publish(self, event: DomainEvent) -> None:
        handlers = list(self._subs.get(event.name, ()))
        if not handlers:
            return
        # Independent: one handler failing does not stop the others.
        # The drainer is the layer that decides retry policy.
        for h in handlers:
            try:
                await h(event)
            except Exception as e:
                logger.error(
                    "bus.handler_failed",
                    extra={
                        "event_name": event.name,
                        "event_id": event.id,
                        "handler": getattr(h, "__qualname__", repr(h)),
                        "error_class": type(e).__name__,
                    },
                )
                raise  # let the drainer's retry policy decide what to do


def event_from_envelope(envelope: dict[str, Any]) -> DomainEvent:
    """Reconstruct a DomainEvent from the JSONB envelope written by the outbox."""
    actor = envelope.get("actor") or {}
    return DomainEvent(
        id=envelope["id"],
        name=envelope["name"],
        version=int(envelope.get("version", 1)),
        occurred_at=datetime.fromisoformat(envelope["occurredAt"]),
        emitted_at=datetime.fromisoformat(envelope["emittedAt"]),
        workspace_id=envelope.get("workspaceId"),
        actor_kind=actor.get("kind", "system"),
        actor_id=actor.get("id"),
        correlation_id=envelope.get("correlationId") or envelope["id"],
        causation_id=envelope.get("causationId"),
        payload=envelope.get("payload", {}),
    )
