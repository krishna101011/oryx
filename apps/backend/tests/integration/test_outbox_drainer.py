"""Outbox drainer end-to-end against Postgres (Phase 3 exit checklist).

Covers: exactly-once delivery on success, retry persistence on transient
handler failure, dead-letter promotion on poison, and the cleanup job.
Runs only when ANANT_TEST_DB is set (with migrations applied).
"""
from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

pytestmark = pytest.mark.requires_db


@pytest.fixture
def sm():
    # Local engine per test module; avoids the app's cached global engine.
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(os.environ["ANANT_TEST_DB"])
    return async_sessionmaker(bind=engine, expire_on_commit=False)


async def _enqueue(sm, name: str = "intake.item.received") -> uuid.UUID:
    from anant.core.models import OutboxEvent
    from anant.services.queue.outbox import make_event_envelope

    env = make_event_envelope(name=name, payload={"n": 1}, workspace_id=None)
    row_id = uuid.UUID(env["id"])
    async with sm() as session:
        session.add(
            OutboxEvent(id=row_id, event_name=name, event=env, workspace_id=None)
        )
        await session.commit()
    return row_id


@pytest.mark.asyncio
async def test_drainer_delivers_exactly_once(sm) -> None:
    from anant.core.models import OutboxEvent
    from anant.services.queue.bus import InProcessBus
    from anant.services.queue.drainer import OutboxDrainer

    name = f"test.delivery.{uuid.uuid4().hex[:8]}"
    row_id = await _enqueue(sm, name)

    seen: list[str] = []
    bus = InProcessBus()

    async def handler(ev) -> None:
        seen.append(ev.id)

    bus.subscribe(name, handler)
    drainer = OutboxDrainer(sm, bus)

    await drainer.drain_once()
    await drainer.drain_once()  # second pass must not redeliver

    assert seen == [str(row_id)]
    async with sm() as session:
        row = await session.get(OutboxEvent, row_id)
        assert row is not None and row.delivered_at is not None


@pytest.mark.asyncio
async def test_drainer_retries_then_succeeds(sm) -> None:
    from anant.core.models import OutboxEvent
    from anant.services.queue.bus import InProcessBus
    from anant.services.queue.drainer import OutboxDrainer

    name = f"test.retry.{uuid.uuid4().hex[:8]}"
    row_id = await _enqueue(sm, name)

    calls = {"n": 0}
    bus = InProcessBus()

    async def flaky(ev) -> None:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("first attempt fails")

    bus.subscribe(name, flaky)
    drainer = OutboxDrainer(sm, bus)

    await drainer.drain_once()
    async with sm() as session:
        row = await session.get(OutboxEvent, row_id)
        assert row.attempts == 1
        assert row.delivered_at is None
        # Force the row due again so the test doesn't wait out the backoff.
        row.last_attempt_at = datetime.now(UTC) - timedelta(hours=1)
        await session.commit()

    await drainer.drain_once()
    async with sm() as session:
        row = await session.get(OutboxEvent, row_id)
        assert row.delivered_at is not None
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_poison_event_moves_to_dead_letter(sm) -> None:
    from anant.core.models import OutboxDeadLetter, OutboxEvent
    from anant.services.queue.bus import InProcessBus
    from anant.services.queue.drainer import OutboxDrainer, PermanentDeliveryError

    name = f"test.poison.{uuid.uuid4().hex[:8]}"
    row_id = await _enqueue(sm, name)

    bus = InProcessBus()

    async def poison(ev) -> None:
        raise PermanentDeliveryError("unprocessable")

    bus.subscribe(name, poison)
    await OutboxDrainer(sm, bus).drain_once()

    async with sm() as session:
        assert await session.get(OutboxEvent, row_id) is None
        result = await session.execute(
            select(OutboxDeadLetter).where(OutboxDeadLetter.original_id == row_id)
        )
        dl = result.scalar_one()
        assert "unprocessable" in dl.final_error


@pytest.mark.asyncio
async def test_cleanup_prunes_old_delivered_rows(sm) -> None:
    from anant.core.models import OutboxEvent
    from anant.services.queue.bus import InProcessBus
    from anant.services.queue.drainer import OutboxDrainer

    name = f"test.cleanup.{uuid.uuid4().hex[:8]}"
    row_id = await _enqueue(sm, name)
    async with sm() as session:
        row = await session.get(OutboxEvent, row_id)
        row.delivered_at = datetime.now(UTC) - timedelta(days=8)
        await session.commit()

    await OutboxDrainer(sm, InProcessBus()).run_cleanup()

    async with sm() as session:
        assert await session.get(OutboxEvent, row_id) is None
