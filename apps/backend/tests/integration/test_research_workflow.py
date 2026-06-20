"""Research workspace + packet workflow end-to-end (Wave E)."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

pytestmark = pytest.mark.requires_db


async def _seed(sm) -> dict:
    from oryx.core.models import Account, IntakeSource, Workspace

    now = datetime.now(UTC)
    async with sm() as session:
        account = Account(
            id=uuid.uuid4(),
            email=f"res+{uuid.uuid4().hex[:8]}@oryx.test",
            password_hash="x",
            password_changed_at=now,
            status="active",
        )
        session.add(account)
        await session.flush()
        workspace = Workspace(
            id=uuid.uuid4(), name="Research WS", owner_account_id=account.id
        )
        session.add(workspace)
        await session.flush()
        source = IntakeSource(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            kind="rss",
            name="feed",
            enabled=True,
            config={},
            origin_kind="custom",
            status="healthy",
        )
        session.add(source)
        await session.commit()
        return {
            "account": account.id,
            "workspace": workspace.id,
            "source": source.id,
        }


async def _make_object(sm, ids: dict, *, status: str = "verified") -> uuid.UUID:
    """Ingest an item and insert one intelligence object with a given status."""
    from oryx.core.models import IntelligenceObject
    from oryx.services.intake.providers.base import RawItem
    from oryx.services.intake.service import IntakeService

    now = datetime.now(UTC)
    async with sm() as session:
        res = await IntakeService(session).ingest_raw_item(
            workspace_id=ids["workspace"],
            intake_source_id=ids["source"],
            provider_name="rss",
            raw=RawItem(
                external_id=f"i-{uuid.uuid4().hex[:8]}",
                received_at=now,
                sender="Wire",
                subject=f"Obj {uuid.uuid4().hex[:6]}",
                body_text="body",
                body_html=None,
                links=[],
                payload={},
            ),
        )
        item_id = res.intake_item_id
        assert item_id is not None
        obj = IntelligenceObject(
            id=uuid.uuid4(),
            workspace_id=ids["workspace"],
            intake_item_id=item_id,
            epistemic_type="claim",
            confidence_score=0.7,
            verification_status=status,
            claim_ids=[],
            conflict_ids=[],
            key_facts={},
            headline="An object",
            scoring_version=1,
        )
        session.add(obj)
        await session.commit()
        return obj.id


def _svc(sm):
    from oryx.services.research.service import ResearchService

    return ResearchService(sm)


async def _new_ws(sm, ids, name="WS-1"):
    ws = await _svc(sm).create_workspace(
        workspace_id=ids["workspace"],
        account_id=ids["account"],
        name=name,
        description="desc",
    )
    return ws.id


@pytest.mark.asyncio
async def test_create_and_list_workspaces(sm) -> None:
    ids = await _seed(sm)
    rws_id = await _new_ws(sm, ids, "Alpha")
    rows = await _svc(sm).list_workspaces(
        workspace_id=ids["workspace"], account_id=ids["account"]
    )
    assert any(r.id == rws_id and r.name == "Alpha" for r in rows)


@pytest.mark.asyncio
async def test_workspace_detail_item_count(sm) -> None:
    ids = await _seed(sm)
    rws_id = await _new_ws(sm, ids)
    ws, count = await _svc(sm).get_workspace_detail(
        workspace_id=ids["workspace"], rws_id=rws_id
    )
    assert ws.id == rws_id
    assert count == 0


@pytest.mark.asyncio
async def test_update_workspace(sm) -> None:
    ids = await _seed(sm)
    rws_id = await _new_ws(sm, ids)
    updated = await _svc(sm).update_workspace(
        workspace_id=ids["workspace"],
        rws_id=rws_id,
        name="Renamed",
        description=None,
        status="archived",
    )
    assert updated.name == "Renamed"
    assert updated.status == "archived"


@pytest.mark.asyncio
async def test_add_list_remove_item(sm) -> None:
    ids = await _seed(sm)
    rws_id = await _new_ws(sm, ids)
    obj_id = await _make_object(sm, ids)
    await _svc(sm).add_item(
        workspace_id=ids["workspace"],
        rws_id=rws_id,
        account_id=ids["account"],
        object_id=obj_id,
        note="pin",
    )
    pairs = await _svc(sm).list_items(workspace_id=ids["workspace"], rws_id=rws_id)
    assert len(pairs) == 1
    item, obj = pairs[0]
    assert item.note == "pin"
    assert obj is not None and obj.id == obj_id

    await _svc(sm).remove_item(
        workspace_id=ids["workspace"], rws_id=rws_id, object_id=obj_id
    )
    pairs2 = await _svc(sm).list_items(workspace_id=ids["workspace"], rws_id=rws_id)
    assert pairs2 == []


@pytest.mark.asyncio
async def test_add_item_note_too_long_rejected(sm) -> None:
    from oryx.core.errors import BadRequestError

    ids = await _seed(sm)
    rws_id = await _new_ws(sm, ids)
    obj_id = await _make_object(sm, ids)
    with pytest.raises(BadRequestError):
        await _svc(sm).add_item(
            workspace_id=ids["workspace"],
            rws_id=rws_id,
            account_id=ids["account"],
            object_id=obj_id,
            note="x" * 501,
        )


@pytest.mark.asyncio
async def test_add_item_note_exactly_500_ok(sm) -> None:
    ids = await _seed(sm)
    rws_id = await _new_ws(sm, ids)
    obj_id = await _make_object(sm, ids)
    await _svc(sm).add_item(
        workspace_id=ids["workspace"],
        rws_id=rws_id,
        account_id=ids["account"],
        object_id=obj_id,
        note="x" * 500,
    )
    pairs = await _svc(sm).list_items(workspace_id=ids["workspace"], rws_id=rws_id)
    assert len(pairs[0][0].note) == 500


@pytest.mark.asyncio
async def test_create_packet_and_get(sm) -> None:
    ids = await _seed(sm)
    rws_id = await _new_ws(sm, ids)
    obj_id = await _make_object(sm, ids)
    packet = await _svc(sm).create_packet(
        workspace_id=ids["workspace"],
        rws_id=rws_id,
        name="Packet 1",
        object_ids=[obj_id],
    )
    assert packet.status == "assembling"
    fetched = await _svc(sm).get_packet(
        workspace_id=ids["workspace"], packet_id=packet.id
    )
    assert fetched.id == packet.id
    assert obj_id in fetched.intelligence_object_ids


@pytest.mark.asyncio
async def test_readiness_clean_is_ready(sm) -> None:
    ids = await _seed(sm)
    rws_id = await _new_ws(sm, ids)
    obj_id = await _make_object(sm, ids, status="verified")
    packet = await _svc(sm).create_packet(
        workspace_id=ids["workspace"], rws_id=rws_id, name="P", object_ids=[obj_id]
    )
    readiness = await _svc(sm).check_readiness(
        workspace_id=ids["workspace"], packet_id=packet.id
    )
    assert readiness.is_ready is True


@pytest.mark.asyncio
async def test_readiness_rejected_blocks(sm) -> None:
    ids = await _seed(sm)
    rws_id = await _new_ws(sm, ids)
    obj_id = await _make_object(sm, ids, status="analyst_rejected")
    packet = await _svc(sm).create_packet(
        workspace_id=ids["workspace"], rws_id=rws_id, name="P", object_ids=[obj_id]
    )
    readiness = await _svc(sm).check_readiness(
        workspace_id=ids["workspace"], packet_id=packet.id
    )
    assert readiness.is_ready is False
    assert "rejected" in readiness.blockers[0]


@pytest.mark.asyncio
async def test_mark_ready_blocked_returns_409(sm) -> None:
    from oryx.core.errors import PreconditionFailedError

    ids = await _seed(sm)
    rws_id = await _new_ws(sm, ids)
    obj_id = await _make_object(sm, ids, status="contested")
    packet = await _svc(sm).create_packet(
        workspace_id=ids["workspace"], rws_id=rws_id, name="P", object_ids=[obj_id]
    )
    with pytest.raises(PreconditionFailedError) as exc:
        await _svc(sm).mark_ready(
            workspace_id=ids["workspace"], packet_id=packet.id
        )
    assert exc.value.http_status == 409
    assert exc.value.details["blockers"]


@pytest.mark.asyncio
async def test_acknowledge_unblocks_then_ready(sm) -> None:
    from oryx.core.models import OutboxEvent, ResearchPacket
    from oryx.services.research.events.constants import PACKET_READY

    ids = await _seed(sm)
    rws_id = await _new_ws(sm, ids)
    obj_id = await _make_object(sm, ids, status="contested")
    packet = await _svc(sm).create_packet(
        workspace_id=ids["workspace"], rws_id=rws_id, name="P", object_ids=[obj_id]
    )
    await _svc(sm).acknowledge_conflict(
        workspace_id=ids["workspace"], packet_id=packet.id, object_id=obj_id
    )
    ready = await _svc(sm).mark_ready(
        workspace_id=ids["workspace"], packet_id=packet.id
    )
    assert ready.status == "ready"
    assert ready.ready_at is not None
    assert ready.consumed_at is None  # Phase 4 NEVER sets consumed_at

    async with sm() as session:
        events = (
            await session.execute(
                select(OutboxEvent).where(
                    OutboxEvent.event_name == PACKET_READY,
                    OutboxEvent.workspace_id == ids["workspace"],
                )
            )
        ).scalars().all()
        assert len(events) == 1
        assert events[0].event["payload"]["packetId"] == str(packet.id)
        packet_row = await session.get(ResearchPacket, packet.id)
        assert packet_row.consumed_at is None


@pytest.mark.asyncio
async def test_list_packets_by_status(sm) -> None:
    ids = await _seed(sm)
    rws_id = await _new_ws(sm, ids)
    obj_id = await _make_object(sm, ids, status="verified")
    packet = await _svc(sm).create_packet(
        workspace_id=ids["workspace"], rws_id=rws_id, name="P", object_ids=[obj_id]
    )
    await _svc(sm).mark_ready(workspace_id=ids["workspace"], packet_id=packet.id)
    ready = await _svc(sm).list_packets(
        workspace_id=ids["workspace"], status="ready"
    )
    assembling = await _svc(sm).list_packets(
        workspace_id=ids["workspace"], status="assembling"
    )
    assert any(p.id == packet.id for p in ready)
    assert all(p.id != packet.id for p in assembling)


@pytest.mark.asyncio
async def test_me_count_helpers(sm) -> None:
    from oryx.services.research.repository import ResearchRepository

    ids = await _seed(sm)
    rws_id = await _new_ws(sm, ids)
    obj_id = await _make_object(sm, ids, status="verified")
    packet = await _svc(sm).create_packet(
        workspace_id=ids["workspace"], rws_id=rws_id, name="P", object_ids=[obj_id]
    )
    await _svc(sm).mark_ready(workspace_id=ids["workspace"], packet_id=packet.id)
    async with sm() as session:
        repo = ResearchRepository(session)
        assert (
            await repo.count_active_workspaces(
                workspace_id=ids["workspace"], account_id=ids["account"]
            )
            == 1
        )
        assert await repo.count_ready_packets(ids["workspace"]) == 1
