"""Command Center "Today" feed (2026-07-11) — GET /v1/intake/items/recent.

The dashboard shows the REAL ingested content (normalized subject + source
name), not the generic "New item ingested" activity_inbox rows. Pins: newest
first, soft-deleted items excluded, un-normalized items included with a null
subject (outer join — a fresh ingest the normalizer hasn't reached must still
appear), workspace scoping, and the limit parameter.
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


async def _signup(client) -> tuple[dict, uuid.UUID]:
    signup = await client.post(
        "/v1/auth/signup",
        json={
            "email": f"today+{uuid.uuid4().hex[:8]}@oryx.test",
            "password": "StrongPass123",
            "displayName": "Today",
            "deviceId": str(uuid.uuid4()),
            "deviceLabel": "iPhone",
            "devicePlatform": "ios",
        },
    )
    access = signup.json()["data"]["tokens"]["accessToken"]
    headers = {"Authorization": f"Bearer {access}"}
    me = (await client.get("/v1/auth/me", headers=headers)).json()["data"]
    return headers, uuid.UUID(me["workspace"]["id"])


async def _seed_source(session, *, ws_id, name="Yahoo Finance"):
    from oryx.core.models import IntakeSource

    source = IntakeSource(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        kind="rss",
        name=name,
        enabled=True,
        config={},
        origin_kind="custom",
        status="healthy",
    )
    session.add(source)
    await session.flush()
    return source


async def _seed_item(
    session,
    *,
    ws_id,
    source,
    received_at,
    subject: str | None = "unset",
    deleted: bool = False,
):
    """One intake item; subject=None seeds a normalized row with a null
    subject, subject='unset' (sentinel) seeds NO normalized row at all."""
    from oryx.core.models import IntakeItem, IntakeItemNormalized

    item = IntakeItem(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        intake_source_id=source.id,
        provider_name="rss",
        external_id=f"x-{uuid.uuid4().hex[:8]}",
        received_at=received_at,
        payload={},
        fingerprint=uuid.uuid4().hex,
        deleted_at=datetime.now(UTC) if deleted else None,
    )
    session.add(item)
    await session.flush()
    if subject != "unset":
        session.add(
            IntakeItemNormalized(
                intake_item_id=item.id,
                subject=subject,
                body_text="body",
                links=[],
                item_metadata={},
                normalizer_version=1,
            )
        )
        await session.flush()
    return item


@pytest.mark.asyncio
async def test_recent_items_show_real_content_newest_first(app, sm) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://t"
    ) as client:
        headers, ws_id = await _signup(client)
        now = datetime.now(UTC)

        async with sm() as session:
            source = await _seed_source(session, ws_id=ws_id)
            oldest = await _seed_item(
                session, ws_id=ws_id, source=source,
                received_at=now - timedelta(hours=2), subject="Oldest headline",
            )
            newest = await _seed_item(
                session, ws_id=ws_id, source=source,
                received_at=now, subject="Newest headline",
            )
            # Ingested but not yet normalized — must still appear, subject null.
            unnormalized = await _seed_item(
                session, ws_id=ws_id, source=source,
                received_at=now - timedelta(hours=1), subject="unset",
            )
            # Soft-deleted — must never appear.
            await _seed_item(
                session, ws_id=ws_id, source=source,
                received_at=now + timedelta(hours=1), subject="Deleted headline",
                deleted=True,
            )
            await session.commit()

        res = await client.get("/v1/intake/items/recent", headers=headers)
        assert res.status_code == 200
        rows = res.json()["data"]

    assert [r["id"] for r in rows] == [str(newest.id), str(unnormalized.id), str(oldest.id)]
    assert rows[0] == {
        "id": str(newest.id),
        "subject": "Newest headline",
        "sourceName": "Yahoo Finance",
        "providerName": "rss",
        "receivedAt": rows[0]["receivedAt"],  # shape-checked below
    }
    assert rows[0]["receivedAt"] is not None
    assert rows[1]["subject"] is None  # un-normalized, not dropped
    assert all(r["subject"] != "Deleted headline" for r in rows)


@pytest.mark.asyncio
async def test_recent_items_is_workspace_scoped(app, sm) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://t"
    ) as client:
        headers_a, ws_a = await _signup(client)
        _headers_b, ws_b = await _signup(client)
        now = datetime.now(UTC)

        async with sm() as session:
            source_a = await _seed_source(session, ws_id=ws_a, name="A Feed")
            source_b = await _seed_source(session, ws_id=ws_b, name="B Feed")
            mine = await _seed_item(
                session, ws_id=ws_a, source=source_a, received_at=now,
                subject="Mine",
            )
            await _seed_item(
                session, ws_id=ws_b, source=source_b, received_at=now,
                subject="Not mine",
            )
            await session.commit()

        res = await client.get("/v1/intake/items/recent", headers=headers_a)
        rows = res.json()["data"]

    assert [r["id"] for r in rows] == [str(mine.id)]


@pytest.mark.asyncio
async def test_recent_items_respects_limit(app, sm) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://t"
    ) as client:
        headers, ws_id = await _signup(client)
        now = datetime.now(UTC)

        async with sm() as session:
            source = await _seed_source(session, ws_id=ws_id)
            for i in range(12):
                await _seed_item(
                    session, ws_id=ws_id, source=source,
                    received_at=now - timedelta(minutes=i), subject=f"H{i}",
                )
            await session.commit()

        default = (await client.get("/v1/intake/items/recent", headers=headers)).json()["data"]
        limited = (
            await client.get("/v1/intake/items/recent?limit=3", headers=headers)
        ).json()["data"]

    assert len(default) == 10  # default limit
    assert len(limited) == 3
    assert [r["subject"] for r in limited] == ["H0", "H1", "H2"]  # still newest first
