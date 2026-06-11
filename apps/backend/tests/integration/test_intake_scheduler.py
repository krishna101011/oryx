"""SourceSyncRunner end-to-end against Postgres.

Uses a fake provider injected through the runner's provider_factory seam,
so the full pipeline (claim → ingest → dedupe → outbox → cursor + health
persistence) runs against real tables with zero network.
Runs only when ANANT_TEST_DB is set (with migrations applied).
"""
from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

pytestmark = pytest.mark.requires_db


@pytest.fixture
def sm():
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(os.environ["ANANT_TEST_DB"])
    return async_sessionmaker(bind=engine, expire_on_commit=False)


async def _make_source(sm, *, kind: str = "rss") -> tuple[uuid.UUID, uuid.UUID]:
    """Create account → workspace → intake_source; return (workspace_id, source_id)."""
    from anant.core.models import Account, IntakeSource, Workspace

    async with sm() as session:
        account = Account(
            id=uuid.uuid4(),
            email=f"sched+{uuid.uuid4().hex[:8]}@anant.test",
            password_hash="x",
            password_changed_at=datetime.now(UTC),
            status="active",
        )
        session.add(account)
        await session.flush()
        workspace = Workspace(
            id=uuid.uuid4(), name="Sched Test", owner_account_id=account.id
        )
        session.add(workspace)
        await session.flush()
        source = IntakeSource(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            kind=kind,
            name="fixture source",
            enabled=True,
            config={"feed_url": "https://example.test/feed.xml"},
            origin_kind="custom",
            status="healthy",
        )
        session.add(source)
        await session.commit()
        return workspace.id, source.id


def _raw_item(n: int):
    from anant.services.intake.providers.base import RawItem

    return RawItem(
        external_id=f"ext-{n}-{uuid.uuid4().hex[:6]}",
        received_at=datetime.now(UTC),
        sender="Example Feed",
        subject=f"Item {n} {uuid.uuid4().hex[:6]}",
        body_text="body",
        body_html=None,
        links=[{"url": f"https://example.test/{n}", "anchor": "link"}],
        payload={"n": n},
    )


class FakeRssProvider:
    """Protocol-shaped fake: yields canned items, exposes a real RssSyncReport."""

    name = "rss"

    def __init__(self, items: int = 2, error: Exception | None = None) -> None:
        self._items = items
        self._error = error
        self.last_report = None

    async def validate_config(self, config):  # pragma: no cover — unused here
        raise NotImplementedError

    async def sync(self, *, workspace_id, intake_source_id, cursor, config):
        from anant.services.intake.providers.rss.sync import RssSyncReport

        if self._error is not None:
            raise self._error
        for n in range(self._items):
            yield _raw_item(n)
        self.last_report = RssSyncReport(
            new_etag="etag-1",
            new_last_modified="Mon, 08 Jun 2026 00:00:00 GMT",
            items_yielded=self._items,
            permanent_redirect_to=None,
        )


@pytest.mark.asyncio
async def test_sync_ingests_items_and_persists_cursor_and_health(sm) -> None:
    from anant.core.models import IntakeAuditLog, IntakeItem, IntakeSource, OutboxEvent
    from anant.services.intake.sync_runner import SourceSyncRunner, SyncOutcome

    workspace_id, source_id = await _make_source(sm)
    provider = FakeRssProvider(items=2)
    runner = SourceSyncRunner(sm, provider_factory=lambda snap, _sm: provider)

    outcome = await runner.sync_source(source_id)
    assert outcome == SyncOutcome.COMPLETED

    async with sm() as session:
        items = (
            await session.execute(
                select(IntakeItem).where(IntakeItem.intake_source_id == source_id)
            )
        ).scalars().all()
        assert len(items) == 2

        outbox = (
            await session.execute(
                select(OutboxEvent).where(OutboxEvent.workspace_id == workspace_id)
            )
        ).scalars().all()
        assert len(outbox) == 2
        assert all(r.event_name == "intake.item.received" for r in outbox)

        src = await session.get(IntakeSource, source_id)
        assert src.status == "healthy"
        assert src.consecutive_failures == 0
        assert src.cursor == {
            "etag": "etag-1",
            "last_modified": "Mon, 08 Jun 2026 00:00:00 GMT",
        }
        assert src.last_synced_at is not None

        events = {
            row.event
            for row in (
                await session.execute(
                    select(IntakeAuditLog).where(
                        IntakeAuditLog.intake_source_id == source_id
                    )
                )
            ).scalars().all()
        }
        assert {"sync_start", "sync_complete"} <= events


@pytest.mark.asyncio
async def test_auth_failure_marks_source_auth_required(sm) -> None:
    from anant.core.models import IntakeAuditLog, IntakeSource
    from anant.services.intake.providers.errors import ProviderError, ProviderErrorKind
    from anant.services.intake.sync_runner import SourceSyncRunner, SyncOutcome

    _, source_id = await _make_source(sm)
    provider = FakeRssProvider(
        error=ProviderError(kind=ProviderErrorKind.AUTH, message="401 from vendor")
    )
    runner = SourceSyncRunner(sm, provider_factory=lambda snap, _sm: provider)

    outcome = await runner.sync_source(source_id)
    assert outcome == SyncOutcome.FAILED

    async with sm() as session:
        src = await session.get(IntakeSource, source_id)
        assert src.status == "auth_required"
        assert src.consecutive_failures == 1
        events = {
            row.event
            for row in (
                await session.execute(
                    select(IntakeAuditLog).where(
                        IntakeAuditLog.intake_source_id == source_id
                    )
                )
            ).scalars().all()
        }
        assert {"sync_failed", "auth_lapsed"} <= events


@pytest.mark.asyncio
async def test_circuit_breaker_degrades_after_threshold(sm) -> None:
    from anant.core.models import IntakeAuditLog, IntakeSource
    from anant.services.intake.providers.errors import ProviderError, ProviderErrorKind
    from anant.services.intake.sync_runner import (
        CIRCUIT_BREAK_THRESHOLD,
        SourceSyncRunner,
    )

    _, source_id = await _make_source(sm)
    async with sm() as session:
        src = await session.get(IntakeSource, source_id)
        src.consecutive_failures = CIRCUIT_BREAK_THRESHOLD - 1
        await session.commit()

    # RATE_LIMITED never sets a final status itself, so only the breaker
    # can flip this source to degraded.
    provider = FakeRssProvider(
        error=ProviderError(
            kind=ProviderErrorKind.RATE_LIMITED, message="429", retry_after_seconds=30
        )
    )
    runner = SourceSyncRunner(sm, provider_factory=lambda snap, _sm: provider)
    await runner.sync_source(source_id)

    async with sm() as session:
        src = await session.get(IntakeSource, source_id)
        assert src.status == "degraded"
        assert src.consecutive_failures == CIRCUIT_BREAK_THRESHOLD
        events = {
            row.event
            for row in (
                await session.execute(
                    select(IntakeAuditLog).where(
                        IntakeAuditLog.intake_source_id == source_id
                    )
                )
            ).scalars().all()
        }
        assert "circuit_broken" in events


@pytest.mark.asyncio
async def test_duplicate_items_are_skipped_not_reinserted(sm) -> None:
    from anant.core.models import IntakeItem
    from anant.services.intake.sync_runner import SourceSyncRunner

    _, source_id = await _make_source(sm)
    item = _raw_item(0)

    class RepeatingProvider(FakeRssProvider):
        async def sync(self, *, workspace_id, intake_source_id, cursor, config):
            from anant.services.intake.providers.rss.sync import RssSyncReport

            yield item
            yield item  # exact duplicate within one sync
            self.last_report = RssSyncReport(
                new_etag=None, new_last_modified=None,
                items_yielded=2, permanent_redirect_to=None,
            )

    runner = SourceSyncRunner(
        sm, provider_factory=lambda snap, _sm: RepeatingProvider()
    )
    await runner.sync_source(source_id)

    async with sm() as session:
        items = (
            await session.execute(
                select(IntakeItem).where(IntakeItem.intake_source_id == source_id)
            )
        ).scalars().all()
        assert len(items) == 1
