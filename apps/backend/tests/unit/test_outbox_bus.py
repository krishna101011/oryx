"""InProcessBus + outbox envelope shape."""
from __future__ import annotations

import uuid

import pytest

from oryx.services.queue.bus import (
    DomainEvent,
    InProcessBus,
    event_from_envelope,
)
from oryx.services.queue.outbox import make_event_envelope


def test_envelope_has_all_required_fields() -> None:
    env = make_event_envelope(
        name="intake.item.received",
        payload={"x": 1},
        workspace_id=uuid.uuid4(),
    )
    for key in (
        "id", "name", "version", "occurredAt", "emittedAt",
        "workspaceId", "actor", "correlationId", "causationId", "payload",
    ):
        assert key in env


def test_envelope_default_correlation_id_equals_event_id() -> None:
    env = make_event_envelope(name="x", payload={}, workspace_id=None)
    assert env["correlationId"] == env["id"]


def test_event_from_envelope_round_trips() -> None:
    env = make_event_envelope(
        name="intake.item.received",
        payload={"intakeItemId": "abc"},
        workspace_id=uuid.uuid4(),
    )
    event = event_from_envelope(env)
    assert event.name == env["name"]
    assert event.payload["intakeItemId"] == "abc"


@pytest.mark.asyncio
async def test_bus_routes_to_subscribed_handler() -> None:
    bus = InProcessBus()
    received: list[DomainEvent] = []

    async def handler(ev: DomainEvent) -> None:
        received.append(ev)

    bus.subscribe("intake.item.received", handler)
    env = make_event_envelope(
        name="intake.item.received", payload={}, workspace_id=None
    )
    await bus.publish(event_from_envelope(env))
    assert len(received) == 1


@pytest.mark.asyncio
async def test_bus_ignores_unsubscribed_event_names() -> None:
    bus = InProcessBus()
    env = make_event_envelope(name="nothing.listening", payload={}, workspace_id=None)
    # Should not raise even though no handler exists.
    await bus.publish(event_from_envelope(env))


@pytest.mark.asyncio
async def test_bus_propagates_handler_exceptions_to_drainer() -> None:
    """Per the comment in bus.py — handler failures bubble so the drainer
    can apply its retry policy."""
    bus = InProcessBus()

    async def bad_handler(ev: DomainEvent) -> None:
        raise RuntimeError("nope")

    bus.subscribe("e", bad_handler)
    env = make_event_envelope(name="e", payload={}, workspace_id=None)
    with pytest.raises(RuntimeError):
        await bus.publish(event_from_envelope(env))
