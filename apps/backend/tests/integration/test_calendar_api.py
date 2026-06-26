"""Phase 5 Wave E — calendar HTTP surface (schedule → list → cancel).

End-to-end over HTTP: the router wiring, capability deps, snake_case request /
camelCase response shape, and the soft-cancel convention.
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


async def _signup(client: AsyncClient, sm) -> tuple[str, str, uuid.UUID]:
    from sqlalchemy import select

    from oryx.core.models import Account, WorkspaceMember

    email = f"cal+{uuid.uuid4().hex[:8]}@oryx.test"
    res = await client.post(
        "/v1/auth/signup",
        json={
            "email": email,
            "password": "StrongPass123",
            "displayName": "Cal User",
            "deviceId": str(uuid.uuid4()),
            "deviceLabel": "Pytest",
            "devicePlatform": "ios",
        },
    )
    assert res.status_code == 200, res.text
    token = res.json()["data"]["tokens"]["accessToken"]
    async with sm() as session:
        account = (
            await session.execute(select(Account).where(Account.email == email))
        ).scalar_one()
        member = (
            await session.execute(
                select(WorkspaceMember).where(WorkspaceMember.account_id == account.id)
            )
        ).scalar_one()
        return token, str(member.workspace_id), account.id


async def _seed_approved_draft(sm, *, workspace_id: str, account_id: uuid.UUID):
    from oryx.core.models import (
        ContentDraft,
        DraftVersion,
        ResearchPacket,
        ResearchWorkspace,
    )

    now = datetime.now(UTC)
    ws = uuid.UUID(workspace_id)
    async with sm() as session:
        rws = ResearchWorkspace(
            id=uuid.uuid4(), account_id=account_id, workspace_id=ws, name="RW"
        )
        session.add(rws)
        await session.flush()
        packet = ResearchPacket(
            id=uuid.uuid4(),
            research_workspace_id=rws.id,
            workspace_id=ws,
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
            workspace_id=ws,
            account_id=account_id,
            packet_id=packet.id,
            format="article",
            title="API Schedulable",
            status="approved",
            current_version=1,
            generation_model="claude-sonnet-4-6",
            generation_version=1,
            word_count=2,
        )
        session.add(draft)
        await session.flush()
        session.add(
            DraftVersion(
                id=uuid.uuid4(),
                draft_id=draft.id,
                version_number=1,
                content="Body text",
                edited_by=account_id,
                is_ai_generated=True,
                word_count=2,
            )
        )
        await session.commit()
        return draft.id


@pytest.mark.asyncio
async def test_schedule_list_cancel_over_http(sm, app) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://t"
    ) as client:
        token, ws, acct = await _signup(client, sm)
        headers = {"Authorization": f"Bearer {token}"}
        draft_id = await _seed_approved_draft(sm, workspace_id=ws, account_id=acct)

        target = await client.post(
            "/v1/targets",
            headers=headers,
            json={
                "name": "Hook",
                "channel": "webhook",
                "credentials": {"secret": "s"},
                "config": {"url": "https://example.test/hook"},
            },
        )
        assert target.status_code == 200, target.text
        target_id = target.json()["data"]["id"]

        when = (datetime.now(UTC) + timedelta(days=1)).isoformat()
        scheduled = await client.post(
            "/v1/calendar",
            headers=headers,
            json={
                "draft_id": str(draft_id),
                "target_id": target_id,
                "scheduled_at": when,
            },
        )
        assert scheduled.status_code == 200, scheduled.text
        body = scheduled.json()["data"]
        assert body["status"] == "scheduled"
        assert body["draftId"] == str(draft_id)
        assert body["targetId"] == target_id
        entry_id = body["id"]

        # range list returns the entry
        start = (datetime.now(UTC) - timedelta(days=1)).isoformat()
        end = (datetime.now(UTC) + timedelta(days=2)).isoformat()
        listed = await client.get(
            "/v1/calendar",
            headers=headers,
            params={"start_date": start, "end_date": end},
        )
        assert listed.status_code == 200, listed.text
        ids = [e["id"] for e in listed.json()["data"]]
        assert entry_id in ids

        # soft cancel — returns the row, status flipped, row NOT deleted
        cancelled = await client.delete(
            f"/v1/calendar/{entry_id}", headers=headers
        )
        assert cancelled.status_code == 200, cancelled.text
        assert cancelled.json()["data"]["status"] == "cancelled"

        # still present in a range list (soft delete, row retained)
        listed2 = await client.get(
            "/v1/calendar",
            headers=headers,
            params={"start_date": start, "end_date": end},
        )
        ids2 = [e["id"] for e in listed2.json()["data"]]
        assert entry_id in ids2


@pytest.mark.asyncio
async def test_schedule_past_time_rejected_over_http(sm, app) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://t"
    ) as client:
        token, ws, acct = await _signup(client, sm)
        headers = {"Authorization": f"Bearer {token}"}
        draft_id = await _seed_approved_draft(sm, workspace_id=ws, account_id=acct)
        target = await client.post(
            "/v1/targets",
            headers=headers,
            json={
                "name": "Hook",
                "channel": "webhook",
                "credentials": {"secret": "s"},
                "config": {"url": "https://example.test/hook"},
            },
        )
        target_id = target.json()["data"]["id"]
        past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        res = await client.post(
            "/v1/calendar",
            headers=headers,
            json={
                "draft_id": str(draft_id),
                "target_id": target_id,
                "scheduled_at": past,
            },
        )
        assert res.status_code == 400, res.text
