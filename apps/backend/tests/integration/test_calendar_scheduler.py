"""Phase 5 Wave E — CalendarScheduler against Postgres.

Real DB, channel adapters faked via the registry, publishing engine REAL (the
scheduler must call the existing publish_draft, never reimplement it). Asserts:

  PASS A:
    - within-grace entry fires and the calendar status tracks the publish result
    - beyond-grace entry is marked 'failed' WITHOUT calling publish_draft
      (adapter NOT invoked — test-asserted)
    - startup catch-up: an overdue entry is processed on the immediate startup
      pass, not only after the first 60s tick
    - full flow: schedule → tick → publish_draft delivered → status='published'
  PASS B:
    - a pending publication with insufficient elapsed time is NOT re-driven
    - one with sufficient elapsed time IS re-driven (both attempt_count tiers)
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

pytestmark = pytest.mark.requires_db


# --------------------------------------------------------------------------- #
# Fake channel adapters (same shape as the publishing-engine integration test)
# --------------------------------------------------------------------------- #
class _DeliverChannel:
    channel_type = "fake"

    def __init__(self) -> None:
        self.publish_calls = 0

    async def validate_credentials(self, credentials):
        return True

    async def health_check(self, credentials):
        return True

    def format_content(self, content, max_length):
        return [content]

    async def publish(self, content, draft_title, credentials, config, citations=None):
        # citations accepted (optional) for the webhook adapter's post-freeze
        # signature; the scheduler publishes via this fake registered as webhook.
        from oryx.services.publishing.channels.base import PublishResult

        self.publish_calls += 1
        return PublishResult(
            external_id=f"ext-{self.publish_calls}",
            external_url="https://example.test/post",
            status="delivered",
        )


class _TransientFailChannel(_DeliverChannel):
    async def publish(self, content, draft_title, credentials, config, citations=None):
        from oryx.services.publishing.channels.base import TransientChannelError

        self.publish_calls += 1
        raise TransientChannelError("rate limited")


@pytest.fixture
def restore_registry():
    from oryx.services.publishing.channels import registry

    saved = registry.all_channels()
    yield registry
    for key in list(registry.all_channels()):
        if key not in saved:
            del registry._REGISTRY[key]
    for key, adapter in saved.items():
        registry.register_channel(key, adapter)


# --------------------------------------------------------------------------- #
# Seeders
# --------------------------------------------------------------------------- #
async def _seed_approved_draft(sm):
    from oryx.core.models import (
        Account,
        ContentDraft,
        DraftVersion,
        ResearchPacket,
        ResearchWorkspace,
        Workspace,
    )

    now = datetime.now(UTC)
    async with sm() as session:
        account = Account(
            id=uuid.uuid4(),
            email=f"calsch+{uuid.uuid4().hex[:8]}@oryx.test",
            password_hash="x",
            password_changed_at=now,
            status="active",
        )
        session.add(account)
        await session.flush()
        ws = Workspace(id=uuid.uuid4(), name="W", owner_account_id=account.id)
        session.add(ws)
        await session.flush()
        rws = ResearchWorkspace(
            id=uuid.uuid4(), account_id=account.id, workspace_id=ws.id, name="RW"
        )
        session.add(rws)
        await session.flush()
        packet = ResearchPacket(
            id=uuid.uuid4(),
            research_workspace_id=rws.id,
            workspace_id=ws.id,
            name="P",
            status="consumed",
            intelligence_object_ids=[],
            conflict_acknowledged_ids=[],
            ready_at=now,
        )
        session.add(packet)
        await session.flush()
        draft = ContentDraft(
            id=uuid.uuid4(),
            workspace_id=ws.id,
            account_id=account.id,
            packet_id=packet.id,
            format="article",
            title="Schedulable Draft",
            status="approved",
            current_version=1,
            generation_model="claude-sonnet-4-6",
            generation_version=1,
            word_count=3,
        )
        session.add(draft)
        await session.flush()
        session.add(
            DraftVersion(
                id=uuid.uuid4(),
                draft_id=draft.id,
                version_number=1,
                content="The body content.",
                edited_by=account.id,
                is_ai_generated=True,
                word_count=3,
            )
        )
        await session.commit()
        return ws.id, account.id, draft.id


async def _make_target(sm, *, workspace_id, channel="webhook", name="T"):
    from oryx.core.credential_crypto import encrypt_credentials
    from oryx.core.models import PublishTarget

    ct, iv = encrypt_credentials({"secret": "s"})
    async with sm() as session:
        target = PublishTarget(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            name=name,
            channel=channel,
            credentials=ct,
            credentials_iv=iv,
            config={},
            is_active=True,
        )
        session.add(target)
        await session.commit()
        return target.id


async def _insert_entry(sm, *, ws_id, draft_id, target_id, account_id, scheduled_at):
    """Insert a calendar_entries row directly (bypassing the future-time guard so
    we can stage overdue / beyond-grace entries) and promote the draft."""
    from oryx.core.models import CalendarEntry
    from oryx.services.drafts.repository import DraftsRepository

    async with sm() as session:
        entry = CalendarEntry(
            id=uuid.uuid4(),
            workspace_id=ws_id,
            draft_id=draft_id,
            target_id=target_id,
            scheduled_at=scheduled_at,
            status="scheduled",
            created_by=account_id,
        )
        session.add(entry)
        await DraftsRepository(session).set_draft_status(
            draft_id=draft_id, status="scheduled"
        )
        await session.commit()
        return entry.id


async def _entry(sm, entry_id):
    from oryx.core.models import CalendarEntry

    async with sm() as session:
        return await session.get(CalendarEntry, entry_id)


# --------------------------------------------------------------------------- #
# PASS A — calendar firing
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_within_grace_entry_fires_and_publishes(sm, restore_registry) -> None:
    """Full flow: schedule (overdue, within grace) → tick → publish_draft
    delivered → calendar_entries.status='published' + publication_id set."""
    from oryx.core.models import CalendarEntry, Publication
    from oryx.services.calendar.scheduler import CalendarScheduler

    fake = _DeliverChannel()
    restore_registry.register_channel("webhook", fake)
    ws_id, account_id, draft_id = await _seed_approved_draft(sm)
    target_id = await _make_target(sm, workspace_id=ws_id)
    entry_id = await _insert_entry(
        sm, ws_id=ws_id, draft_id=draft_id, target_id=target_id,
        account_id=account_id,
        scheduled_at=datetime.now(UTC) - timedelta(minutes=2),  # overdue, in grace
    )

    await CalendarScheduler(sm).tick()

    entry = await _entry(sm, entry_id)
    assert entry.status == "published"
    assert entry.publication_id is not None
    async with sm() as session:
        pub = await session.get(Publication, entry.publication_id)
        assert pub.status == "delivered"
        from oryx.core.models import ContentDraft

        draft = await session.get(ContentDraft, draft_id)
        assert draft.status == "published"
        # exactly one delivered publication for THIS draft (robust to Pass B
        # re-driving unrelated rows in the same global tick).
        from sqlalchemy import func

        delivered = (
            await session.execute(
                select(func.count())
                .select_from(Publication)
                .where(
                    Publication.draft_id == draft_id,
                    Publication.status == "delivered",
                )
            )
        ).scalar_one()
        assert delivered == 1
    assert isinstance(entry, CalendarEntry)


@pytest.mark.asyncio
async def test_beyond_grace_entry_marked_failed_without_publishing(
    sm, restore_registry
) -> None:
    """An entry past the 15-minute grace window is marked 'failed' WITHOUT the
    adapter ever being invoked."""
    from oryx.services.calendar.scheduler import CalendarScheduler

    fake = _DeliverChannel()
    restore_registry.register_channel("webhook", fake)
    ws_id, account_id, draft_id = await _seed_approved_draft(sm)
    target_id = await _make_target(sm, workspace_id=ws_id)
    entry_id = await _insert_entry(
        sm, ws_id=ws_id, draft_id=draft_id, target_id=target_id,
        account_id=account_id,
        scheduled_at=datetime.now(UTC) - timedelta(minutes=20),  # beyond grace
    )

    await CalendarScheduler(sm).tick()

    entry = await _entry(sm, entry_id)
    assert entry.status == "failed"
    assert entry.publication_id is None
    # THE key assertion: publish_draft was NEVER invoked for this entry. The
    # engine inserts a pending publication row BEFORE calling any adapter, so
    # zero publication rows for this draft proves the publish path never ran —
    # robust to Pass B/A acting on other drafts in the same global tick.
    from sqlalchemy import func

    from oryx.core.models import Publication

    async with sm() as session:
        pub_count = (
            await session.execute(
                select(func.count())
                .select_from(Publication)
                .where(Publication.draft_id == draft_id)
            )
        ).scalar_one()
        assert pub_count == 0


@pytest.mark.asyncio
async def test_transient_result_leaves_entry_scheduled(sm, restore_registry) -> None:
    """A transient publish failure leaves the publication 'pending' AND the
    calendar entry 'scheduled' (Pass B re-drives later)."""
    from oryx.services.calendar.scheduler import CalendarScheduler

    fake = _TransientFailChannel()
    restore_registry.register_channel("webhook", fake)
    ws_id, account_id, draft_id = await _seed_approved_draft(sm)
    target_id = await _make_target(sm, workspace_id=ws_id)
    entry_id = await _insert_entry(
        sm, ws_id=ws_id, draft_id=draft_id, target_id=target_id,
        account_id=account_id,
        scheduled_at=datetime.now(UTC) - timedelta(minutes=1),
    )

    await CalendarScheduler(sm).tick()

    entry = await _entry(sm, entry_id)
    assert entry.status == "scheduled"  # not resolved yet
    from oryx.core.models import Publication

    async with sm() as session:
        pub = (
            await session.execute(
                select(Publication).where(Publication.draft_id == draft_id)
            )
        ).scalar_one()
        assert pub.status == "pending"
        assert pub.attempt_count == 1
        assert pub.last_attempt_at is not None  # the Wave E refinement is stamped


@pytest.mark.asyncio
async def test_startup_catch_up_processes_overdue_entry(sm, restore_registry) -> None:
    """run_forever's FIRST pass runs immediately at startup. With a 1-hour tick,
    the only way an overdue entry is processed within the test window is the
    immediate startup pass (not the next 60s tick)."""
    from oryx.services.calendar.scheduler import CalendarScheduler

    fake = _DeliverChannel()
    restore_registry.register_channel("webhook", fake)
    ws_id, account_id, draft_id = await _seed_approved_draft(sm)
    target_id = await _make_target(sm, workspace_id=ws_id)
    entry_id = await _insert_entry(
        sm, ws_id=ws_id, draft_id=draft_id, target_id=target_id,
        account_id=account_id,
        scheduled_at=datetime.now(UTC) - timedelta(minutes=2),
    )

    # tick_seconds=3600 → a tick-driven run would NOT fire within the test.
    scheduler = CalendarScheduler(sm, tick_seconds=3600.0)
    task = asyncio.create_task(scheduler.run_forever())
    try:
        status = "scheduled"
        for _ in range(60):
            await asyncio.sleep(0.05)
            entry = await _entry(sm, entry_id)
            status = entry.status
            if status != "scheduled":
                break
    finally:
        task.cancel()

    # Processed on the immediate startup pass (with tick_seconds=3600, a
    # tick-driven run could not have fired within the test window).
    assert status == "published"


# --------------------------------------------------------------------------- #
# PASS B — transient retry re-drive (backoff)
# --------------------------------------------------------------------------- #
async def _seed_pending_publication(sm, *, attempt_count, last_attempt_at):
    """Seed a draft + target + a publication stuck 'pending' at a given
    attempt_count / last_attempt_at, so Pass B's backoff can be exercised."""
    from oryx.core.models import Publication

    ws_id, account_id, draft_id = await _seed_approved_draft(sm)
    target_id = await _make_target(sm, workspace_id=ws_id)
    pub_id = uuid.uuid4()
    async with sm() as session:
        session.add(
            Publication(
                id=pub_id,
                draft_id=draft_id,
                version_number=1,
                target_id=target_id,
                workspace_id=ws_id,
                status="pending",
                attempt_count=attempt_count,
                last_attempt_at=last_attempt_at,
            )
        )
        await session.commit()
    return ws_id, draft_id, target_id, pub_id


async def _pub(sm, pub_id):
    from oryx.core.models import Publication

    async with sm() as session:
        return await session.get(Publication, pub_id)


# NOTE on isolation: Pass B's list_retry_candidates() is GLOBAL across
# workspaces, so a tick can also touch other tests' leftover pending rows.
# These tests therefore assert on the SPECIFIC seeded publication row's state
# (re-driven ⇒ delivered, skipped ⇒ attempt_count unchanged + still pending),
# never on global counts.
@pytest.mark.asyncio
async def test_redrive_skips_insufficient_elapsed_time(sm, restore_registry) -> None:
    """attempt_count=1 needs 5 min; only 2 have passed → THIS row is NOT
    re-driven (still pending, attempt_count unchanged)."""
    from oryx.services.calendar.scheduler import CalendarScheduler

    restore_registry.register_channel("webhook", _DeliverChannel())
    _, _, _, pub_id = await _seed_pending_publication(
        sm, attempt_count=1, last_attempt_at=datetime.now(UTC) - timedelta(minutes=2)
    )

    await CalendarScheduler(sm).tick()
    pub = await _pub(sm, pub_id)
    assert pub.status == "pending"
    assert pub.attempt_count == 1  # untouched — backoff not elapsed


@pytest.mark.asyncio
async def test_redrive_tier1_after_five_minutes(sm, restore_registry) -> None:
    """attempt_count=1 with 6 min elapsed → re-driven; the engine delivers and
    advances THIS row to 'delivered'."""
    from oryx.services.calendar.scheduler import CalendarScheduler

    restore_registry.register_channel("webhook", _DeliverChannel())
    _, _, _, pub_id = await _seed_pending_publication(
        sm, attempt_count=1, last_attempt_at=datetime.now(UTC) - timedelta(minutes=6)
    )

    await CalendarScheduler(sm).tick()
    pub = await _pub(sm, pub_id)
    assert pub.status == "delivered"


@pytest.mark.asyncio
async def test_redrive_tier2_requires_thirty_minutes(sm, restore_registry) -> None:
    """attempt_count=2: 6 min is NOT enough (tier-2 waits 30) but 31 min IS — the
    second tier, distinct from tier 1. Asserts on each seeded row directly."""
    from oryx.services.calendar.scheduler import CalendarScheduler

    # insufficient for tier 2 (6 min < 30 min)
    restore_registry.register_channel("webhook", _DeliverChannel())
    _, _, _, pub_id_a = await _seed_pending_publication(
        sm, attempt_count=2, last_attempt_at=datetime.now(UTC) - timedelta(minutes=6)
    )
    await CalendarScheduler(sm).tick()
    pub_a = await _pub(sm, pub_id_a)
    assert pub_a.status == "pending"
    assert pub_a.attempt_count == 2  # not re-driven

    # sufficient for tier 2 (31 min ≥ 30 min)
    restore_registry.register_channel("webhook", _DeliverChannel())
    _, _, _, pub_id_b = await _seed_pending_publication(
        sm, attempt_count=2, last_attempt_at=datetime.now(UTC) - timedelta(minutes=31)
    )
    await CalendarScheduler(sm).tick()
    pub_b = await _pub(sm, pub_id_b)
    assert pub_b.status == "delivered"
