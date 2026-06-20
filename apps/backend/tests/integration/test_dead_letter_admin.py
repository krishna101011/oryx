"""Dead-letter admin endpoints end-to-end (§12.3 ops surface).

Covers: platform-admin gating (workspace owner denied), list with envelope,
replay restores a fresh outbox row, discard removes the entry.
Runs only when ORYX_TEST_DB is set (with migrations applied).
"""
from __future__ import annotations

import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

pytestmark = pytest.mark.requires_db


@pytest.fixture
def app():
    os.environ.setdefault("DATABASE_URL", os.environ["ORYX_TEST_DB"])
    from oryx.main import create_app
    return create_app()


async def _signup(client: AsyncClient) -> tuple[str, str]:
    """Returns (access_token, email)."""
    email = f"dladmin+{uuid.uuid4().hex[:8]}@oryx.test"
    res = await client.post(
        "/v1/auth/signup",
        json={
            "email": email,
            "password": "StrongPass123",
            "displayName": "DL Admin",
            "deviceId": str(uuid.uuid4()),
            "deviceLabel": "Pytest Device",
            "devicePlatform": "ios",
        },
    )
    assert res.status_code == 200, res.text
    return res.json()["data"]["tokens"]["accessToken"], email


async def _promote_to_platform_admin(sm, email: str) -> None:
    from oryx.core.models import Account

    async with sm() as session:
        account = (
            await session.execute(select(Account).where(Account.email == email))
        ).scalar_one()
        account.is_platform_admin = True
        await session.commit()


async def _seed_dead_letter(sm) -> uuid.UUID:
    from oryx.core.models import OutboxDeadLetter
    from oryx.services.queue.outbox import make_event_envelope

    env = make_event_envelope(
        name="intake.item.received", payload={"seed": True}, workspace_id=None
    )
    row = OutboxDeadLetter(
        id=uuid.uuid4(),
        original_id=uuid.UUID(env["id"]),
        event_name=env["name"],
        event=env,
        workspace_id=None,
        final_error="seeded poison event",
        total_attempts=20,
    )
    async with sm() as session:
        session.add(row)
        await session.commit()
    return row.id


@pytest.mark.asyncio
async def test_workspace_owner_without_platform_flag_is_denied(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        token, _ = await _signup(client)
        res = await client.get(
            "/v1/admin/intake/dead-letter",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_platform_admin_lists_dead_letter_entries(app, sm) -> None:
    dl_id = await _seed_dead_letter(sm)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        token, email = await _signup(client)
        await _promote_to_platform_admin(sm, email)
        res = await client.get(
            "/v1/admin/intake/dead-letter",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert res.status_code == 200, res.text
    body = res.json()
    assert "pagination" in body["meta"]
    ids = {entry["id"] for entry in body["data"]}
    assert str(dl_id) in ids


@pytest.mark.asyncio
async def test_replay_moves_entry_back_to_outbox(app, sm) -> None:
    from oryx.core.models import OutboxDeadLetter, OutboxEvent

    dl_id = await _seed_dead_letter(sm)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        token, email = await _signup(client)
        await _promote_to_platform_admin(sm, email)
        res = await client.post(
            f"/v1/admin/intake/dead-letter/{dl_id}/replay",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert res.status_code == 200, res.text
    outbox_id = uuid.UUID(res.json()["data"]["outboxEventId"])

    async with sm() as session:
        assert await session.get(OutboxDeadLetter, dl_id) is None
        replayed = await session.get(OutboxEvent, outbox_id)
        assert replayed is not None
        assert replayed.delivered_at is None
        assert replayed.attempts == 0
        assert replayed.event["payload"] == {"seed": True}


@pytest.mark.asyncio
async def test_discard_removes_entry(app, sm) -> None:
    from oryx.core.models import OutboxDeadLetter

    dl_id = await _seed_dead_letter(sm)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        token, email = await _signup(client)
        await _promote_to_platform_admin(sm, email)
        res = await client.post(
            f"/v1/admin/intake/dead-letter/{dl_id}/discard",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert res.status_code == 200, res.text
    assert res.json()["data"] == {"discarded": True}

    async with sm() as session:
        assert await session.get(OutboxDeadLetter, dl_id) is None


@pytest.mark.asyncio
async def test_replay_of_unknown_id_returns_not_found(app, sm) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        token, email = await _signup(client)
        await _promote_to_platform_admin(sm, email)
        res = await client.post(
            f"/v1/admin/intake/dead-letter/{uuid.uuid4()}/replay",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert res.status_code == 404
