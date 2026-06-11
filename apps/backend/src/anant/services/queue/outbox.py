"""Outbox writer.

This is the *write side* of the outbox pattern (ADR-014 Stage B / ADR-018).
The drainer (queue/drainer.py — Batch 2) reads + publishes. This module is
called from inside every intake transaction so that a `DomainEvent` lands
atomically with the rows it describes.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from anant.core.models import OutboxEvent


def make_event_envelope(
    *,
    name: str,
    payload: dict[str, Any],
    workspace_id: uuid.UUID | None,
    actor_kind: str = "system",
    actor_id: str | None = None,
    correlation_id: str | None = None,
    causation_id: str | None = None,
    version: int = 1,
) -> dict[str, Any]:
    """Build the canonical DomainEvent shape (mirrors ADR-014 §2.2)."""
    now = datetime.now(UTC).isoformat()
    event_id = str(uuid.uuid4())
    return {
        "id": event_id,
        "name": name,
        "version": version,
        "occurredAt": now,
        "emittedAt": now,
        "workspaceId": str(workspace_id) if workspace_id else None,
        "actor": {"kind": actor_kind, "id": actor_id},
        "correlationId": correlation_id or event_id,
        "causationId": causation_id,
        "payload": payload,
    }


async def enqueue_event(
    session: AsyncSession,
    *,
    name: str,
    payload: dict[str, Any],
    workspace_id: uuid.UUID | None,
    actor_kind: str = "system",
    actor_id: str | None = None,
    correlation_id: str | None = None,
    causation_id: str | None = None,
) -> uuid.UUID:
    """Insert an outbox row in the current transaction.

    The caller commits as part of the surrounding business transaction —
    that's the whole point of the outbox pattern (no separate publish step
    can fail in between).
    """
    event = make_event_envelope(
        name=name,
        payload=payload,
        workspace_id=workspace_id,
        actor_kind=actor_kind,
        actor_id=actor_id,
        correlation_id=correlation_id,
        causation_id=causation_id,
    )
    row = OutboxEvent(
        id=uuid.UUID(event["id"]),
        event_name=name,
        event=event,
        workspace_id=workspace_id,
    )
    session.add(row)
    await session.flush()
    return row.id
