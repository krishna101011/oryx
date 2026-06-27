"""Phase 5 Wave F — /v1/auth/me content{} counts, end-to-end.

test_contracts.py already pins the SHAPE of the content block; this test pins the
NUMBERS against the real Wave D/E mechanisms that produce them:

  - scheduledCount reflects a draft promoted to 'scheduled' by the REAL Wave E
    CalendarService.schedule_draft (not a hand-set status).
  - publishedThisWeek reflects a draft delivered by the REAL Wave D
    PublishingEngine (status→published, published_at=now) AND correctly EXCLUDES
    a published draft whose published_at is older than the 7-day window.
  - draftCount counts every draft in the workspace; content.pendingReviewCount
    counts only 'in_review'.
"""
from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.requires_db


@pytest.fixture
def app():
    os.environ.setdefault("DATABASE_URL", os.environ["ORYX_TEST_DB"])
    from oryx.main import create_app

    return create_app()


async def _seed_research_workspace(session, *, ws_id, account_id):
    from oryx.core.models import ResearchWorkspace

    rws = ResearchWorkspace(
        id=uuid.uuid4(), account_id=account_id, workspace_id=ws_id, name="RW"
    )
    session.add(rws)
    await session.flush()
    return rws.id


async def _seed_draft(
    session,
    *,
    ws_id,
    account_id,
    rws_id,
    status: str,
    published_at: datetime | None = None,
    with_version: bool = True,
):
    """Create a packet + a content draft (+ version) in a given status."""
    from oryx.core.models import ContentDraft, DraftVersion, ResearchPacket

    now = datetime.now(UTC)
    packet = ResearchPacket(
        id=uuid.uuid4(),
        research_workspace_id=rws_id,
        workspace_id=ws_id,
        name="P",
        status="consumed",
        intelligence_object_ids=[],
        conflict_acknowledged_ids=[],
        ready_at=now,
        consumed_at=now,
    )
    session.add(packet)
    await session.flush()
    draft = ContentDraft(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        account_id=account_id,
        packet_id=packet.id,
        format="article",
        title="Draft",
        status=status,
        current_version=1,
        generation_model="claude-sonnet-4-6",
        generation_version=1,
        word_count=3,
        published_at=published_at,
    )
    session.add(draft)
    await session.flush()
    if with_version:
        session.add(
            DraftVersion(
                id=uuid.uuid4(),
                draft_id=draft.id,
                version_number=1,
                content="The body content.",
                edited_by=account_id,
                is_ai_generated=True,
                word_count=3,
            )
        )
        await session.flush()
    return draft.id


async def _make_export_target(session, *, ws_id):
    from oryx.core.credential_crypto import encrypt_credentials
    from oryx.core.models import PublishTarget

    ct, iv = encrypt_credentials({})
    target = PublishTarget(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        name="Export",
        channel="export",
        credentials=ct,
        credentials_iv=iv,
        config={},
        is_active=True,
    )
    session.add(target)
    await session.flush()
    return target.id


@pytest.mark.asyncio
async def test_me_content_counts_reflect_wave_d_and_e(app, sm, tmp_path) -> None:
    from oryx.services.calendar.service import CalendarService
    from oryx.services.publishing.engine import PublishingEngine

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://t"
    ) as client:
        signup = await client.post(
            "/v1/auth/signup",
            json={
                "email": f"counts+{uuid.uuid4().hex[:8]}@oryx.test",
                "password": "StrongPass123",
                "displayName": "Counter",
                "deviceId": str(uuid.uuid4()),
                "deviceLabel": "iPhone",
                "devicePlatform": "ios",
            },
        )
        access = signup.json()["data"]["tokens"]["accessToken"]
        headers = {"Authorization": f"Bearer {access}"}
        me = (await client.get("/v1/auth/me", headers=headers)).json()["data"]
        account_id = uuid.UUID(me["account"]["id"])
        ws_id = uuid.UUID(me["workspace"]["id"])
        # Brand-new account: no content yet.
        assert me["content"] == {
            "draftCount": 0,
            "pendingReviewCount": 0,
            "scheduledCount": 0,
            "publishedThisWeek": 0,
        }

        # ---- Seed five drafts in distinct lifecycle states ----------------
        async with sm() as session:
            rws_id = await _seed_research_workspace(
                session, ws_id=ws_id, account_id=account_id
            )
            await _seed_draft(
                session, ws_id=ws_id, account_id=account_id, rws_id=rws_id,
                status="draft",
            )
            await _seed_draft(
                session, ws_id=ws_id, account_id=account_id, rws_id=rws_id,
                status="in_review",
            )
            to_schedule = await _seed_draft(
                session, ws_id=ws_id, account_id=account_id, rws_id=rws_id,
                status="approved",
            )
            to_publish = await _seed_draft(
                session, ws_id=ws_id, account_id=account_id, rws_id=rws_id,
                status="approved",
            )
            # An OLD published draft — must NOT count toward publishedThisWeek.
            await _seed_draft(
                session, ws_id=ws_id, account_id=account_id, rws_id=rws_id,
                status="published",
                published_at=datetime.now(UTC) - timedelta(days=10),
            )
            target_id = await _make_export_target(session, ws_id=ws_id)
            await session.commit()

        # ---- Wave E: schedule one approved draft (→ 'scheduled') ----------
        await CalendarService(sm).schedule_draft(
            draft_id=to_schedule,
            target_id=target_id,
            scheduled_at=datetime.now(UTC) + timedelta(days=1),
            account_id=account_id,
            workspace_id=ws_id,
        )

        # ---- Wave D: publish one approved draft (→ 'published', now) ------
        async with sm() as session:
            # Point the export writer at a temp dir so the test leaves no files.
            from oryx.core.models import PublishTarget

            tgt = await session.get(PublishTarget, target_id)
            tgt.config = {"base_dir": str(tmp_path)}
            await session.commit()
        results = await PublishingEngine(sm).publish_draft(
            draft_id=to_publish,
            target_ids=[target_id],
            workspace_id=ws_id,
            account_id=account_id,
        )
        assert results[0].status == "delivered"

        # ---- /me now reflects all of it ----------------------------------
        me2 = (await client.get("/v1/auth/me", headers=headers)).json()["data"]
        content = me2["content"]

    assert content["draftCount"] == 5  # every draft in the workspace
    assert content["pendingReviewCount"] == 1  # only the in_review one
    assert content["scheduledCount"] == 1  # Wave E calendar-scheduled draft
    assert content["publishedThisWeek"] == 1  # the fresh publication; old one excluded
