"""Single-item detail (2026-07-12) — GET /v1/intake/items/{item_id}.

The endpoint behind two formerly-decorative surfaces: an Activity "New item
ingested" row (whose payload carries intakeItemId) and a web search result.
Pins: full normalized content (subject/body/sender/links) plus source name,
the un-normalized outer-join contract (no 404 just because the normalizer
hasn't run), workspace scoping, soft-delete exclusion, and 404 for unknown ids.
Seeding mirrors test_intake_recent_items.py.
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


async def _signup(client) -> tuple[dict, uuid.UUID]:
    signup = await client.post(
        "/v1/auth/signup",
        json={
            "email": f"itemdetail+{uuid.uuid4().hex[:8]}@oryx.test",
            "password": "StrongPass123",
            "displayName": "Detail",
            "deviceId": str(uuid.uuid4()),
            "deviceLabel": "iPhone",
            "devicePlatform": "ios",
        },
    )
    access = signup.json()["data"]["tokens"]["accessToken"]
    headers = {"Authorization": f"Bearer {access}"}
    me = (await client.get("/v1/auth/me", headers=headers)).json()["data"]
    return headers, uuid.UUID(me["workspace"]["id"])


async def _seed_source(session, *, ws_id, name="Reuters Markets"):
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
    normalized: bool = True,
    deleted: bool = False,
):
    from oryx.core.models import IntakeItem, IntakeItemNormalized

    item = IntakeItem(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        intake_source_id=source.id,
        provider_name="rss",
        external_id=f"x-{uuid.uuid4().hex[:8]}",
        received_at=datetime(2026, 7, 11, 14, 30, tzinfo=UTC),
        payload={},
        fingerprint=uuid.uuid4().hex,
        deleted_at=datetime.now(UTC) if deleted else None,
    )
    session.add(item)
    await session.flush()
    if normalized:
        session.add(
            IntakeItemNormalized(
                intake_item_id=item.id,
                sender_label="Reuters",
                sender_domain="reuters.com",
                subject="Fed holds rates steady",
                body_text="The Federal Reserve held rates steady on Wednesday.",
                links=[{"url": "https://reuters.com/fed", "anchor": "Full story"}],
                item_metadata={},
                normalizer_version=1,
            )
        )
        await session.flush()
    return item


@pytest.mark.asyncio
async def test_item_detail_returns_full_real_content(app, sm) -> None:
    """A normalized item resolves with headline, source, sender, body, and the
    extracted links — everything the detail screen renders."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://t"
    ) as client:
        headers, ws_id = await _signup(client)
        async with sm() as session:
            source = await _seed_source(session, ws_id=ws_id)
            item = await _seed_item(session, ws_id=ws_id, source=source)
            await session.commit()

        res = await client.get(f"/v1/intake/items/{item.id}", headers=headers)
        assert res.status_code == 200
        data = res.json()["data"]

    assert data == {
        "id": str(item.id),
        "subject": "Fed holds rates steady",
        "bodyText": "The Federal Reserve held rates steady on Wednesday.",
        "senderLabel": "Reuters",
        "senderDomain": "reuters.com",
        "links": [{"url": "https://reuters.com/fed", "anchor": "Full story"}],
        "sourceName": "Reuters Markets",
        "providerName": "rss",
        "receivedAt": data["receivedAt"],  # presence-checked below
    }
    assert data["receivedAt"] is not None


@pytest.mark.asyncio
async def test_item_detail_unnormalized_item_still_resolves(app, sm) -> None:
    """An item the normalizer hasn't reached yet must NOT 404 — it resolves
    with null content fields, matching /items/recent's outer-join contract."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://t"
    ) as client:
        headers, ws_id = await _signup(client)
        async with sm() as session:
            source = await _seed_source(session, ws_id=ws_id)
            item = await _seed_item(
                session, ws_id=ws_id, source=source, normalized=False
            )
            await session.commit()

        res = await client.get(f"/v1/intake/items/{item.id}", headers=headers)
        assert res.status_code == 200
        data = res.json()["data"]

    assert data["subject"] is None
    assert data["bodyText"] is None
    assert data["links"] == []
    assert data["sourceName"] == "Reuters Markets"  # the join half still real


@pytest.mark.asyncio
async def test_item_detail_is_workspace_scoped(app, sm) -> None:
    """Another workspace's item id 404s — never leaks across workspaces."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://t"
    ) as client:
        headers_a, _ws_a = await _signup(client)
        _headers_b, ws_b = await _signup(client)
        async with sm() as session:
            source_b = await _seed_source(session, ws_id=ws_b, name="B Feed")
            item_b = await _seed_item(session, ws_id=ws_b, source=source_b)
            await session.commit()

        res = await client.get(f"/v1/intake/items/{item_b.id}", headers=headers_a)
        assert res.status_code == 404


@pytest.mark.asyncio
async def test_item_detail_soft_deleted_item_404s(app, sm) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://t"
    ) as client:
        headers, ws_id = await _signup(client)
        async with sm() as session:
            source = await _seed_source(session, ws_id=ws_id)
            item = await _seed_item(
                session, ws_id=ws_id, source=source, deleted=True
            )
            await session.commit()

        res = await client.get(f"/v1/intake/items/{item.id}", headers=headers)
        assert res.status_code == 404


@pytest.mark.asyncio
async def test_item_detail_unknown_id_404s_and_unauthenticated_401s(app) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://t"
    ) as client:
        headers, _ws_id = await _signup(client)
        res = await client.get(
            f"/v1/intake/items/{uuid.uuid4()}", headers=headers
        )
        assert res.status_code == 404

    # A FRESH client: signup left a session cookie on the one above (dual-auth
    # read path), which would make its bare request authenticated anyway.
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://t"
    ) as anon:
        res = await anon.get(f"/v1/intake/items/{uuid.uuid4()}")
        assert res.status_code == 401
