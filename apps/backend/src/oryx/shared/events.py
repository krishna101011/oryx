"""Event bus interface.

Phase 1 ships only the interface (Protocol). The first real EventBus
implementation lands in Phase 3 (in-process), with the outbox pattern
arriving in Phase 4 and an external broker in Phase 6.

See docs/adr/ADR-014-event-architecture.md for the full rationale.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Protocol

ActorKind = Literal["account", "system", "provider"]


@dataclass(frozen=True)
class DomainEvent:
    """Canonical domain event envelope.

    Mirrors the TypeScript interface in shared-types (will be generated in
    Phase 3 when the first real events ship).
    """

    id: str
    name: str
    version: int
    occurred_at: datetime
    emitted_at: datetime
    workspace_id: str | None
    actor_kind: ActorKind
    actor_id: str | None
    correlation_id: str
    causation_id: str | None
    payload: dict[str, Any]


EventHandler = Callable[[DomainEvent], Awaitable[None]]


class EventBus(Protocol):
    """Publishes domain events and routes them to subscribers."""

    async def publish(self, event: DomainEvent) -> None: ...

    def subscribe(self, name: str, handler: EventHandler) -> None: ...
