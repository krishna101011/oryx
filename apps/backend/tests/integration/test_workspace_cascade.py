"""CR-6 workspace deletion cascade against Postgres.

Exit-checklist items: upstream revoke best-effort (failure → orphan
table), local credentials always deleted, no orphan rows, no
cross-workspace leakage, idempotent re-run.
Runs only when ANANT_TEST_DB is set (with migrations applied).
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

pytestmark = pytest.mark.requires_db


async def _seed_workspace_with_intake(sm) -> tuple[uuid.UUID, uuid.UUID]:
    """Workspace + gmail source + credentials + one ingested item + queue rows."""
    from anant.core.models import (
        Account,
        IntakeSource,
        WebhookIdempotencyKey,
        Workspace,
    )
    from anant.services.intake.credentials import IntakeCredentialsRepository
    from anant.services.intake.providers.base import RawItem
    from anant.services.intake.service import IntakeService

    async with sm() as session:
        account = Account(
            id=uuid.uuid4(),
            email=f"cascade+{uuid.uuid4().hex[:8]}@anant.test",
            password_hash="x",
            password_changed_at=datetime.now(UTC),
            status="active",
        )
        session.add(account)
        await session.flush()
        workspace = Workspace(
            id=uuid.uuid4(), name="Cascade WS", owner_account_id=account.id
        )
        session.add(workspace)
        await session.flush()
        source = IntakeSource(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            kind="gmail",
            name="inbox",
            enabled=True,
            config={},
            origin_kind="custom",
            status="healthy",
        )
        session.add(source)
        await session.flush()
        await IntakeCredentialsRepository(session).store(
            intake_source_id=source.id,
            workspace_id=workspace.id,
            token=b"access-token",
            refresh_token=b"refresh-token",
            token_expires_at=None,
        )
        await IntakeService(session).ingest_raw_item(
            workspace_id=workspace.id,
            intake_source_id=source.id,
            provider_name="gmail",
            raw=RawItem(
                external_id=f"msg-{uuid.uuid4().hex[:8]}",
                received_at=datetime.now(UTC),
                sender="Someone <s@example.com>",
                subject="Cascade fixture",
                body_text="body",
                body_html=None,
                links=[],
                payload={},
            ),
        )
        session.add(
            WebhookIdempotencyKey(
                workspace_id=workspace.id,
                intake_source_id=source.id,
                idempotency_key="k1",
            )
        )
        await session.commit()
        return workspace.id, source.id


async def _count(sm, model, workspace_id: uuid.UUID) -> int:
    async with sm() as session:
        result = await session.execute(
            select(func.count()).select_from(model).where(
                model.workspace_id == workspace_id
            )
        )
        return int(result.scalar_one())


@pytest.mark.asyncio
async def test_cascade_removes_every_workspace_scoped_row(sm) -> None:
    from anant.core.models import (
        IntakeAuditLog,
        IntakeCredentials,
        IntakeDedupeIndex,
        IntakeItem,
        IntakeSource,
        OutboxEvent,
        WebhookIdempotencyKey,
    )
    from anant.services.intake.workspace_cascade import (
        cascade_workspace_intake_deletion,
    )

    ws_id, _ = await _seed_workspace_with_intake(sm)

    async def revoke_ok(kind: str, token: str) -> bool:
        return True

    report = await cascade_workspace_intake_deletion(sm, ws_id, revoke=revoke_ok)
    assert report.sources_deleted == 1
    assert report.credentials_deleted == 1
    assert report.items_deleted == 1
    assert report.revoke_failures == 0

    for model in (
        IntakeSource, IntakeCredentials, IntakeItem, IntakeDedupeIndex,
        IntakeAuditLog, WebhookIdempotencyKey, OutboxEvent,
    ):
        assert await _count(sm, model, ws_id) == 0, model.__name__


@pytest.mark.asyncio
async def test_failed_revoke_lands_in_orphan_table_but_creds_still_deleted(sm) -> None:
    from anant.core.models import IntakeCredentials, WorkspaceDeletionOrphanCredential
    from anant.services.intake.workspace_cascade import (
        cascade_workspace_intake_deletion,
    )

    ws_id, source_id = await _seed_workspace_with_intake(sm)

    async def revoke_fails(kind: str, token: str) -> bool:
        return False

    report = await cascade_workspace_intake_deletion(sm, ws_id, revoke=revoke_fails)
    assert report.revoke_failures == 1
    assert report.credentials_deleted == 1  # local delete is unconditional

    async with sm() as session:
        orphan = (
            await session.execute(
                select(WorkspaceDeletionOrphanCredential).where(
                    WorkspaceDeletionOrphanCredential.workspace_id == ws_id
                )
            )
        ).scalar_one()
        assert orphan.intake_source_id == source_id
        assert orphan.provider_kind == "gmail"
    assert await _count(sm, IntakeCredentials, ws_id) == 0


@pytest.mark.asyncio
async def test_cascade_does_not_touch_other_workspaces(sm) -> None:
    from anant.core.models import IntakeItem, IntakeSource
    from anant.services.intake.workspace_cascade import (
        cascade_workspace_intake_deletion,
    )

    victim_ws, _ = await _seed_workspace_with_intake(sm)
    survivor_ws, _ = await _seed_workspace_with_intake(sm)

    async def revoke_ok(kind: str, token: str) -> bool:
        return True

    await cascade_workspace_intake_deletion(sm, victim_ws, revoke=revoke_ok)

    assert await _count(sm, IntakeSource, survivor_ws) == 1
    assert await _count(sm, IntakeItem, survivor_ws) == 1


@pytest.mark.asyncio
async def test_cascade_is_idempotent(sm) -> None:
    from anant.services.intake.workspace_cascade import (
        cascade_workspace_intake_deletion,
    )

    ws_id, _ = await _seed_workspace_with_intake(sm)

    async def revoke_ok(kind: str, token: str) -> bool:
        return True

    first = await cascade_workspace_intake_deletion(sm, ws_id, revoke=revoke_ok)
    second = await cascade_workspace_intake_deletion(sm, ws_id, revoke=revoke_ok)
    assert first.sources_deleted == 1
    assert second.sources_deleted == 0
    assert second.items_deleted == 0
    assert second.revoke_failures == 0


@pytest.mark.asyncio
async def test_lifecycle_events_survive_the_cascade(sm) -> None:
    from anant.core.models import OutboxEvent
    from anant.services.intake.workspace_cascade import (
        cascade_workspace_intake_deletion,
    )

    ws_id, _ = await _seed_workspace_with_intake(sm)

    async def revoke_ok(kind: str, token: str) -> bool:
        return True

    await cascade_workspace_intake_deletion(sm, ws_id, revoke=revoke_ok)

    async with sm() as session:
        rows = (
            await session.execute(
                select(OutboxEvent).where(
                    OutboxEvent.event_name == "workspace.deletion.completed"
                )
            )
        ).scalars().all()
        ours = [r for r in rows if r.event["payload"].get("workspaceId") == str(ws_id)]
        assert len(ours) >= 1
        # Platform event: routing column is NULL so the cascade's own outbox
        # delete can never reap it.
        assert all(r.workspace_id is None for r in ours)
