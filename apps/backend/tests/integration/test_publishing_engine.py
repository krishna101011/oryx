"""Phase 5 Wave D — publishing engine (idempotency, retry, partial failure).

Real Postgres; channel adapters faked via the registry. Asserts the mandatory
guarantees:
  - double-publish ⇒ exactly ONE delivered publication (DB unique index)
  - PermanentChannelError ⇒ failed, never retried
  - TransientChannelError ⇒ retried up to 5 engine attempts, then failed
  - partial failure (2 succeed, 1 fails) ⇒ draft published; 2 delivered + 1 failed
    in ONE call, and the failure does not roll back the successes
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

pytestmark = pytest.mark.requires_db


# --------------------------------------------------------------------------- #
# Fake channel adapters
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
        # citations is accepted (optional) so this fake satisfies the webhook
        # adapter's post-freeze signature; non-webhook channels are never passed it.
        from oryx.services.publishing.channels.base import PublishResult

        self.publish_calls += 1
        self.last_citations = citations
        return PublishResult(
            external_id=f"ext-{self.publish_calls}",
            external_url="https://example.test/post",
            status="delivered",
        )


class _PermanentFailChannel(_DeliverChannel):
    async def publish(self, content, draft_title, credentials, config):
        from oryx.services.publishing.channels.base import PermanentChannelError

        self.publish_calls += 1
        raise PermanentChannelError("bad credentials")


class _TransientFailChannel(_DeliverChannel):
    async def publish(self, content, draft_title, credentials, config):
        from oryx.services.publishing.channels.base import TransientChannelError

        self.publish_calls += 1
        raise TransientChannelError("rate limited")


@pytest.fixture
def restore_registry():
    """Snapshot + restore the channel registry around a test."""
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
            email=f"pub+{uuid.uuid4().hex[:8]}@oryx.test",
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
            title="Publishable Draft",
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


async def _make_target(sm, *, workspace_id, channel: str, name: str = "T"):
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


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_double_publish_yields_one_delivered(sm, restore_registry) -> None:
    from oryx.core.models import ContentDraft, Publication
    from oryx.services.publishing.engine import PublishingEngine

    fake = _DeliverChannel()
    restore_registry.register_channel("webhook", fake)
    ws_id, account_id, draft_id = await _seed_approved_draft(sm)
    target_id = await _make_target(sm, workspace_id=ws_id, channel="webhook")

    engine = PublishingEngine(sm)
    r1 = await engine.publish_draft(
        draft_id=draft_id, target_ids=[target_id],
        workspace_id=ws_id, account_id=account_id,
    )
    r2 = await engine.publish_draft(
        draft_id=draft_id, target_ids=[target_id],
        workspace_id=ws_id, account_id=account_id,
    )

    assert r1[0].status == "delivered"
    assert r2[0].status == "delivered"
    assert fake.publish_calls == 1  # second call short-circuits on idempotency

    async with sm() as session:
        count = (
            await session.execute(
                select(func.count())
                .select_from(Publication)
                .where(Publication.draft_id == draft_id, Publication.status == "delivered")
            )
        ).scalar_one()
        assert count == 1  # the UNIQUE index guarantees exactly one
        draft = await session.get(ContentDraft, draft_id)
        assert draft.status == "published"
        assert draft.published_at is not None


@pytest.mark.asyncio
async def test_permanent_error_never_retries(sm, restore_registry) -> None:
    from oryx.core.models import ContentDraft, Publication
    from oryx.services.publishing.engine import PublishingEngine

    fake = _PermanentFailChannel()
    restore_registry.register_channel("twitter_x", fake)
    ws_id, account_id, draft_id = await _seed_approved_draft(sm)
    target_id = await _make_target(sm, workspace_id=ws_id, channel="twitter_x")

    engine = PublishingEngine(sm)
    # Even calling twice, a permanent failure must never re-invoke the adapter
    # for a retry beyond the natural one-attempt-per-call.
    res = await engine.publish_draft(
        draft_id=draft_id, target_ids=[target_id],
        workspace_id=ws_id, account_id=account_id,
    )
    assert res[0].status == "failed"
    assert fake.publish_calls == 1

    async with sm() as session:
        pub = (
            await session.execute(select(Publication).where(Publication.draft_id == draft_id))
        ).scalar_one()
        assert pub.status == "failed"
        assert pub.error_message
        # attempt_count is not bumped for permanent failures (no retry semantics).
        assert pub.attempt_count == 0
        draft = await session.get(ContentDraft, draft_id)
        assert draft.status == "approved"  # nothing delivered → still approved


@pytest.mark.asyncio
async def test_transient_retries_to_five_then_fails(sm, restore_registry) -> None:
    from oryx.core.models import Publication
    from oryx.services.publishing.engine import PublishingEngine

    fake = _TransientFailChannel()
    restore_registry.register_channel("notion", fake)
    ws_id, account_id, draft_id = await _seed_approved_draft(sm)
    target_id = await _make_target(sm, workspace_id=ws_id, channel="notion")

    engine = PublishingEngine(sm)
    statuses = []
    for _ in range(5):
        res = await engine.publish_draft(
            draft_id=draft_id, target_ids=[target_id],
            workspace_id=ws_id, account_id=account_id,
        )
        statuses.append(res[0].status)

    # First four attempts stay pending (drainer would re-drive); fifth fails.
    assert statuses == ["pending", "pending", "pending", "pending", "failed"]
    assert fake.publish_calls == 5

    async with sm() as session:
        pub = (
            await session.execute(select(Publication).where(Publication.draft_id == draft_id))
        ).scalar_one()
        assert pub.status == "failed"
        assert pub.attempt_count == 5


@pytest.mark.asyncio
async def test_partial_failure_two_succeed_one_fails(sm, restore_registry) -> None:
    """3 targets, 2 deliver + 1 permanent fail, in ONE publish call:
    draft becomes published, 2 delivered + 1 failed publication, and the
    failure does not roll back the two successful deliveries."""
    from oryx.core.models import ContentDraft, Publication
    from oryx.services.publishing.engine import PublishingEngine

    ok1, ok2, bad = _DeliverChannel(), _DeliverChannel(), _PermanentFailChannel()
    restore_registry.register_channel("twitter_x", ok1)
    restore_registry.register_channel("linkedin", ok2)
    restore_registry.register_channel("notion", bad)

    ws_id, account_id, draft_id = await _seed_approved_draft(sm)
    t1 = await _make_target(sm, workspace_id=ws_id, channel="twitter_x", name="A")
    t2 = await _make_target(sm, workspace_id=ws_id, channel="linkedin", name="B")
    t3 = await _make_target(sm, workspace_id=ws_id, channel="notion", name="C")

    engine = PublishingEngine(sm)
    results = await engine.publish_draft(
        draft_id=draft_id, target_ids=[t1, t2, t3],
        workspace_id=ws_id, account_id=account_id,
    )

    by_status = sorted(r.status for r in results)
    assert by_status == ["delivered", "delivered", "failed"]

    async with sm() as session:
        delivered = (
            await session.execute(
                select(func.count()).select_from(Publication).where(
                    Publication.draft_id == draft_id, Publication.status == "delivered"
                )
            )
        ).scalar_one()
        failed = (
            await session.execute(
                select(func.count()).select_from(Publication).where(
                    Publication.draft_id == draft_id, Publication.status == "failed"
                )
            )
        ).scalar_one()
        assert delivered == 2  # the two successes survived the third's failure
        assert failed == 1
        draft = await session.get(ContentDraft, draft_id)
        assert draft.status == "published"  # at least one delivered


@pytest.mark.asyncio
async def test_publish_non_approved_draft_blocked(sm, restore_registry) -> None:
    from oryx.core.errors import PreconditionFailedError
    from oryx.core.models import ContentDraft
    from oryx.services.publishing.engine import PublishingEngine

    restore_registry.register_channel("webhook", _DeliverChannel())
    ws_id, account_id, draft_id = await _seed_approved_draft(sm)
    async with sm() as session:
        draft = await session.get(ContentDraft, draft_id)
        draft.status = "draft"
        await session.commit()
    target_id = await _make_target(sm, workspace_id=ws_id, channel="webhook")

    with pytest.raises(PreconditionFailedError):
        await PublishingEngine(sm).publish_draft(
            draft_id=draft_id, target_ids=[target_id],
            workspace_id=ws_id, account_id=account_id,
        )


@pytest.mark.asyncio
async def test_content_published_event_emitted(sm, restore_registry) -> None:
    from oryx.core.models import OutboxEvent
    from oryx.services.publishing.engine import PublishingEngine
    from oryx.services.publishing.events.constants import CONTENT_PUBLISHED

    restore_registry.register_channel("export", _DeliverChannel())
    ws_id, account_id, draft_id = await _seed_approved_draft(sm)
    target_id = await _make_target(sm, workspace_id=ws_id, channel="export")

    await PublishingEngine(sm).publish_draft(
        draft_id=draft_id, target_ids=[target_id],
        workspace_id=ws_id, account_id=account_id,
    )

    async with sm() as session:
        ev = (
            await session.execute(
                select(OutboxEvent)
                .where(OutboxEvent.event_name == CONTENT_PUBLISHED)
                .order_by(OutboxEvent.created_at.desc())
            )
        ).scalars().first()
        assert ev is not None
        assert ev.event["payload"]["draftId"] == str(draft_id)
        assert ev.event["payload"]["targetId"] == str(target_id)
