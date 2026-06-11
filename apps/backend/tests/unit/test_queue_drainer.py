"""Drainer delivery policy — backoff, due predicate, retry/dead-letter paths.

DB-free: the drainer's SQL surface is exercised by the requires_db
integration suite; here we fake the session and drive the policy.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from anant.core.models import OutboxEvent
from anant.services.queue.bus import DomainEvent, InProcessBus
from anant.services.queue.dead_letter import MAX_DELIVERY_ATTEMPTS
from anant.services.queue.drainer import (
    DELIVERY_BACKOFF_BASE_SECONDS,
    DELIVERY_BACKOFF_CAP_SECONDS,
    OutboxDrainer,
    PermanentDeliveryError,
    delivery_backoff,
    row_is_due,
)
from anant.services.queue.outbox import make_event_envelope

NOW = datetime(2026, 6, 10, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Pure policy
# ---------------------------------------------------------------------------

def test_backoff_starts_at_base_and_doubles() -> None:
    assert delivery_backoff(0).total_seconds() == DELIVERY_BACKOFF_BASE_SECONDS
    assert delivery_backoff(1).total_seconds() == DELIVERY_BACKOFF_BASE_SECONDS * 2
    assert delivery_backoff(3).total_seconds() == DELIVERY_BACKOFF_BASE_SECONDS * 8


def test_backoff_is_capped() -> None:
    assert delivery_backoff(50).total_seconds() == DELIVERY_BACKOFF_CAP_SECONDS


def test_never_attempted_row_is_due() -> None:
    assert row_is_due(last_attempt_at=None, attempts=0, now=NOW)


def test_recently_failed_row_is_not_due() -> None:
    assert not row_is_due(
        last_attempt_at=NOW - timedelta(seconds=1), attempts=3, now=NOW
    )


def test_row_becomes_due_after_backoff_elapses() -> None:
    assert row_is_due(
        last_attempt_at=NOW - delivery_backoff(3), attempts=3, now=NOW
    )


# ---------------------------------------------------------------------------
# Delivery paths via fakes
# ---------------------------------------------------------------------------

class FakeResult:
    def __init__(self, rows: list) -> None:
        self._rows = rows
        self.rowcount = 0

    def scalars(self) -> FakeResult:
        return self

    def all(self) -> list:
        return self._rows


class FakeSession:
    """Implements just the surface drain_once + dead-letter promotion touch."""

    def __init__(self, rows: list) -> None:
        self._rows = rows
        self.added: list = []
        self.committed = False

    async def __aenter__(self) -> FakeSession:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def execute(self, _stmt: object) -> FakeResult:
        return FakeResult(self._rows)

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True


def _row(*, attempts: int = 0, last_attempt_at: datetime | None = None) -> OutboxEvent:
    env = make_event_envelope(
        name="intake.item.received", payload={"x": 1}, workspace_id=uuid.uuid4()
    )
    return OutboxEvent(
        id=uuid.UUID(env["id"]),
        event_name=env["name"],
        event=env,
        workspace_id=None,
        delivered_at=None,
        attempts=attempts,
        last_attempt_at=last_attempt_at,
    )


def _drainer(rows: list, bus: InProcessBus) -> tuple[OutboxDrainer, FakeSession]:
    session = FakeSession(rows)
    return OutboxDrainer(lambda: session, bus), session


@pytest.mark.asyncio
async def test_successful_delivery_marks_delivered_exactly_once() -> None:
    seen: list[DomainEvent] = []
    bus = InProcessBus()

    async def handler(ev: DomainEvent) -> None:
        seen.append(ev)

    bus.subscribe("intake.item.received", handler)
    row = _row()
    drainer, session = _drainer([row], bus)

    stats = await drainer.drain_once()
    assert stats.delivered == 1
    assert len(seen) == 1
    assert row.delivered_at is not None
    assert session.committed


@pytest.mark.asyncio
async def test_handler_failure_increments_attempts_and_records_error() -> None:
    bus = InProcessBus()

    async def bad(ev: DomainEvent) -> None:
        raise RuntimeError("downstream hiccup")

    bus.subscribe("intake.item.received", bad)
    row = _row()
    drainer, _ = _drainer([row], bus)

    stats = await drainer.drain_once()
    assert stats.retried == 1
    assert row.delivered_at is None
    assert row.attempts == 1
    assert "downstream hiccup" in (row.last_error or "")
    assert row.last_attempt_at is not None


@pytest.mark.asyncio
async def test_permanent_error_dead_letters_immediately() -> None:
    bus = InProcessBus()

    async def poison(ev: DomainEvent) -> None:
        raise PermanentDeliveryError("payload references deleted workspace")

    bus.subscribe("intake.item.received", poison)
    row = _row()
    drainer, session = _drainer([row], bus)

    stats = await drainer.drain_once()
    assert stats.dead_lettered == 1
    # promote_to_dead_letter adds an OutboxDeadLetter row via session.add
    assert any(type(o).__name__ == "OutboxDeadLetter" for o in session.added)


@pytest.mark.asyncio
async def test_attempt_exhaustion_dead_letters() -> None:
    bus = InProcessBus()

    async def bad(ev: DomainEvent) -> None:
        raise RuntimeError("still broken")

    bus.subscribe("intake.item.received", bad)
    # One failure away from the cap; far enough in the past to be due.
    row = _row(
        attempts=MAX_DELIVERY_ATTEMPTS - 1,
        last_attempt_at=NOW - timedelta(days=1),
    )
    drainer, session = _drainer([row], bus)

    stats = await drainer.drain_once()
    assert stats.dead_lettered == 1
    assert any(type(o).__name__ == "OutboxDeadLetter" for o in session.added)


@pytest.mark.asyncio
async def test_not_yet_due_row_is_skipped() -> None:
    bus = InProcessBus()
    row = _row(attempts=5, last_attempt_at=datetime.now(UTC))
    drainer, _ = _drainer([row], bus)

    stats = await drainer.drain_once()
    assert stats.fetched == 1
    assert stats.acted == 0
    assert row.delivered_at is None
