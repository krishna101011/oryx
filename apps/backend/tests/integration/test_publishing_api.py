"""Phase 5 Wave D — targets + publishing HTTP surface.

Asserts the credential-isolation guarantee on the ACTUAL serialized JSON (not
just the schema), plus the create→publish→history flow end-to-end over HTTP
using the Export channel (no external account).
"""
from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.requires_db


@pytest.fixture
def app():
    os.environ.setdefault("DATABASE_URL", os.environ["ORYX_TEST_DB"])
    from oryx.main import create_app

    return create_app()


async def _signup(client: AsyncClient, sm) -> tuple[str, str, uuid.UUID]:
    """Sign up a fresh user (workspace owner → content.write). Returns
    (token, workspace_id, account_id)."""
    from sqlalchemy import select

    from oryx.core.models import Account, WorkspaceMember

    email = f"pub+{uuid.uuid4().hex[:8]}@oryx.test"
    res = await client.post(
        "/v1/auth/signup",
        json={
            "email": email,
            "password": "StrongPass123",
            "displayName": "Pub User",
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


async def _seed_approved_draft(sm, *, workspace_id: str, account_id: uuid.UUID) -> uuid.UUID:
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
            title="API Publishable",
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
async def test_credentials_never_in_serialized_response(sm, app) -> None:
    SECRET = "WEBHOOK-SECRET-DO-NOT-LEAK-xyz789"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        token, _ws, _acct = await _signup(client, sm)
        headers = {"Authorization": f"Bearer {token}"}

        created = await client.post(
            "/v1/targets",
            headers=headers,
            json={
                "name": "My Webhook",
                "channel": "webhook",
                "credentials": {"secret": SECRET},
                "config": {"url": "https://example.test/hook"},
            },
        )
        assert created.status_code == 200, created.text
        # MANDATORY: the secret must not appear anywhere in the create response.
        assert SECRET not in created.text
        assert "credentials" not in created.json()["data"]

        listed = await client.get("/v1/targets", headers=headers)
        assert listed.status_code == 200
        assert SECRET not in listed.text  # raw JSON string check

        target_id = created.json()["data"]["id"]
        got = await client.get(f"/v1/targets/{target_id}", headers=headers)
        assert got.status_code == 200
        assert SECRET not in got.text
        assert "credentials_iv" not in got.text


@pytest.mark.asyncio
async def test_invalid_credentials_rejected(sm, app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        token, _ws, _acct = await _signup(client, sm)
        headers = {"Authorization": f"Bearer {token}"}
        # Twitter requires an access_token — empty creds must 400 and not persist.
        res = await client.post(
            "/v1/targets",
            headers=headers,
            json={"name": "Bad", "channel": "twitter_x", "credentials": {}, "config": {}},
        )
        assert res.status_code == 400
        listed = await client.get("/v1/targets", headers=headers)
        assert listed.json()["data"] == []


@pytest.mark.asyncio
async def test_publish_flow_via_export_channel(sm, app, tmp_path) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        token, ws_id, account_id = await _signup(client, sm)
        headers = {"Authorization": f"Bearer {token}"}

        created = await client.post(
            "/v1/targets",
            headers=headers,
            json={
                "name": "Export",
                "channel": "export",
                "credentials": {},
                "config": {"base_dir": str(tmp_path)},
            },
        )
        assert created.status_code == 200, created.text
        target_id = created.json()["data"]["id"]

        draft_id = await _seed_approved_draft(
            sm, workspace_id=ws_id, account_id=account_id
        )

        published = await client.post(
            f"/v1/drafts/{draft_id}/publish",
            headers=headers,
            json={"target_ids": [target_id]},
        )
        assert published.status_code == 200, published.text
        results = published.json()["data"]
        assert len(results) == 1
        assert results[0]["status"] == "delivered"
        assert results[0]["externalUrl"]  # the written file path

        history = await client.get("/v1/publications", headers=headers)
        assert history.status_code == 200
        pubs = history.json()["data"]
        assert len(pubs) == 1
        assert pubs[0]["status"] == "delivered"
        assert pubs[0]["draftId"] == str(draft_id)


@pytest.mark.asyncio
async def test_delete_target(sm, app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        token, _ws, _acct = await _signup(client, sm)
        headers = {"Authorization": f"Bearer {token}"}
        created = await client.post(
            "/v1/targets",
            headers=headers,
            json={"name": "Tmp", "channel": "export", "credentials": {}, "config": {}},
        )
        target_id = created.json()["data"]["id"]
        deleted = await client.delete(f"/v1/targets/{target_id}", headers=headers)
        assert deleted.status_code == 200
        got = await client.get(f"/v1/targets/{target_id}", headers=headers)
        assert got.status_code == 404
