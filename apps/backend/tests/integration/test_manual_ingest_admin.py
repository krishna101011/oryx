"""Manual ingest endpoint end-to-end (CR-8).

Covers: platform-admin gating, full pipeline (normalize → dedupe →
persist → outbox), dedupe on resubmission, audit trail, validation.
Runs only when ANANT_TEST_DB is set (with migrations applied).
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
    os.environ.setdefault("DATABASE_URL", os.environ["ANANT_TEST_DB"])
    from anant.main import create_app
    return create_app()


@pytest.fixture
def sm():
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(os.environ["ANANT_TEST_DB"])
    return async_sessionmaker(bind=engine, expire_on_commit=False)


async def _admin_with_workspace(client: AsyncClient, sm) -> tuple[str, str]:
    """Signup, promote to platform admin, return (token, workspace_id)."""
    from anant.core.models import Account, WorkspaceMember

    email = f"manual+{uuid.uuid4().hex[:8]}@anant.test"
    res = await client.post(
        "/v1/auth/signup",
        json={
            "email": email,
            "password": "StrongPass123",
            "displayName": "Manual Admin",
            "deviceId": str(uuid.uuid4()),
            "deviceLabel": "Pytest Device",
            "devicePlatform": "ios",
        },
    )
    assert res.status_code == 200, res.text
    token = res.json()["data"]["tokens"]["accessToken"]
    async with sm() as session:
        account = (
            await session.execute(select(Account).where(Account.email == email))
        ).scalar_one()
        account.is_platform_admin = True
        member = (
            await session.execute(
                select(WorkspaceMember).where(WorkspaceMember.account_id == account.id)
            )
        ).scalar_one()
        workspace_id = str(member.workspace_id)
        await session.commit()
    return token, workspace_id


@pytest.mark.asyncio
async def test_non_admin_is_denied(app, sm) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        res = await client.post(
            "/v1/auth/signup",
            json={
                "email": f"plain+{uuid.uuid4().hex[:8]}@anant.test",
                "password": "StrongPass123",
                "displayName": "Plain User",
                "deviceId": str(uuid.uuid4()),
                "deviceLabel": "Pytest Device",
                "devicePlatform": "ios",
            },
        )
        token = res.json()["data"]["tokens"]["accessToken"]
        denied = await client.post(
            "/v1/admin/intake/manual_ingest",
            headers={"Authorization": f"Bearer {token}"},
            json={"workspace_id": str(uuid.uuid4()), "title": "x", "url": "https://e.test/a"},
        )
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_manual_ingest_runs_full_pipeline(app, sm) -> None:
    from anant.core.models import (
        IntakeAuditLog,
        IntakeItem,
        IntakeItemNormalized,
        IntakeSource,
        OutboxEvent,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        token, workspace_id = await _admin_with_workspace(client, sm)
        res = await client.post(
            "/v1/admin/intake/manual_ingest",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "workspace_id": workspace_id,
                "title": f"Manual item {uuid.uuid4().hex[:6]}",
                "url": f"https://example.test/{uuid.uuid4().hex[:8]}",
                "body_text": "pasted analyst note",
            },
        )
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["outcome"] == "inserted"
    item_id = uuid.UUID(data["intakeItemId"])

    async with sm() as session:
        item = await session.get(IntakeItem, item_id)
        assert item is not None
        assert item.provider_name == "manual"
        # Normalization not bypassed
        norm = await session.get(IntakeItemNormalized, item_id)
        assert norm is not None
        # Outbox not bypassed
        outbox = (
            await session.execute(
                select(OutboxEvent).where(
                    OutboxEvent.workspace_id == uuid.UUID(workspace_id),
                    OutboxEvent.event_name == "intake.item.received",
                )
            )
        ).scalars().all()
        assert any(r.event["payload"]["intakeItemId"] == str(item_id) for r in outbox)
        # Operational manual source created once
        src = (
            await session.execute(
                select(IntakeSource).where(
                    IntakeSource.workspace_id == uuid.UUID(workspace_id),
                    IntakeSource.kind == "manual",
                )
            )
        ).scalars().all()
        assert len(src) == 1
        # Audit trail
        audits = (
            await session.execute(
                select(IntakeAuditLog).where(
                    IntakeAuditLog.workspace_id == uuid.UUID(workspace_id),
                    IntakeAuditLog.event == "manual_ingest",
                )
            )
        ).scalars().all()
        assert len(audits) == 1


@pytest.mark.asyncio
async def test_resubmission_dedupes_instead_of_duplicating(app, sm) -> None:
    from anant.core.models import IntakeItem

    url = f"https://example.test/dedupe/{uuid.uuid4().hex[:8]}"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        token, workspace_id = await _admin_with_workspace(client, sm)
        headers = {"Authorization": f"Bearer {token}"}
        body = {"workspace_id": workspace_id, "title": "Same item", "url": url}
        first = await client.post("/v1/admin/intake/manual_ingest", headers=headers, json=body)
        second = await client.post("/v1/admin/intake/manual_ingest", headers=headers, json=body)

    assert first.json()["data"]["outcome"] == "inserted"
    assert second.json()["data"]["outcome"] == "skipped_provider_key"

    async with sm() as session:
        items = (
            await session.execute(
                select(IntakeItem).where(
                    IntakeItem.workspace_id == uuid.UUID(workspace_id)
                )
            )
        ).scalars().all()
        assert len(items) == 1


@pytest.mark.asyncio
async def test_requires_url_or_body_text(app, sm) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        token, workspace_id = await _admin_with_workspace(client, sm)
        res = await client.post(
            "/v1/admin/intake/manual_ingest",
            headers={"Authorization": f"Bearer {token}"},
            json={"workspace_id": workspace_id, "title": "no content"},
        )
    assert res.status_code == 422
