"""Research workspace + packet orchestration (Wave E).

Curation surface for analysts: pin intelligence objects into workspaces, then
assemble packets for the Phase 5 handoff. The readiness gate is enforced here
(HTTP 409 on blockers), not just in the UI. consumed_at is NEVER written by
this code — Phase 5 owns that field.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from oryx.core.errors import (
    BadRequestError,
    NotFoundError,
    PreconditionFailedError,
)
from oryx.core.models import (
    IntelligenceObject,
    ResearchPacket,
    ResearchWorkspace,
    ResearchWorkspaceItem,
)
from oryx.services.queue.outbox import enqueue_event
from oryx.services.research.events.constants import PACKET_READY
from oryx.services.research.models import ReadinessResult
from oryx.services.research.packet_assembler import PacketAssembler
from oryx.services.research.repository import ResearchRepository

NOTE_MAX_LEN = 500


class ResearchService:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker
        self._assembler = PacketAssembler()

    # ---------------- workspaces ----------------

    async def create_workspace(
        self,
        *,
        workspace_id: uuid.UUID,
        account_id: uuid.UUID,
        name: str,
        description: str | None,
    ) -> ResearchWorkspace:
        async with self._sm() as session:
            row = await ResearchRepository(session).create_workspace(
                account_id=account_id,
                workspace_id=workspace_id,
                name=name,
                description=description,
            )
            await session.commit()
            return row

    async def list_workspaces(
        self, *, workspace_id: uuid.UUID, account_id: uuid.UUID
    ) -> list[ResearchWorkspace]:
        async with self._sm() as session:
            return await ResearchRepository(session).list_workspaces(
                workspace_id=workspace_id, account_id=account_id
            )

    async def get_workspace_detail(
        self, *, workspace_id: uuid.UUID, rws_id: uuid.UUID
    ) -> tuple[ResearchWorkspace, int]:
        async with self._sm() as session:
            repo = ResearchRepository(session)
            ws = await repo.get_workspace(workspace_id=workspace_id, rws_id=rws_id)
            if ws is None:
                raise NotFoundError("Research workspace not found")
            count = await repo.count_items(rws_id)
            return ws, count

    async def update_workspace(
        self,
        *,
        workspace_id: uuid.UUID,
        rws_id: uuid.UUID,
        name: str | None,
        description: str | None,
        status: str | None,
    ) -> ResearchWorkspace:
        async with self._sm() as session:
            repo = ResearchRepository(session)
            ws = await repo.get_workspace(workspace_id=workspace_id, rws_id=rws_id)
            if ws is None:
                raise NotFoundError("Research workspace not found")
            await repo.update_workspace(
                rws_id=rws_id, name=name, description=description, status=status
            )
            await session.commit()
            refreshed = await repo.get_workspace(
                workspace_id=workspace_id, rws_id=rws_id
            )
            assert refreshed is not None
            return refreshed

    # ---------------- items ----------------

    async def add_item(
        self,
        *,
        workspace_id: uuid.UUID,
        rws_id: uuid.UUID,
        account_id: uuid.UUID,
        object_id: uuid.UUID,
        note: str | None,
    ) -> dict[str, Any]:
        if note is not None and len(note) > NOTE_MAX_LEN:
            raise BadRequestError(f"Note exceeds {NOTE_MAX_LEN} characters")
        async with self._sm() as session:
            repo = ResearchRepository(session)
            ws = await repo.get_workspace(workspace_id=workspace_id, rws_id=rws_id)
            if ws is None:
                raise NotFoundError("Research workspace not found")
            await repo.add_item(
                rws_id=rws_id, object_id=object_id, added_by=account_id, note=note
            )
            await session.commit()
            return {"researchWorkspaceId": str(rws_id), "intelligenceObjectId": str(object_id)}

    async def remove_item(
        self, *, workspace_id: uuid.UUID, rws_id: uuid.UUID, object_id: uuid.UUID
    ) -> dict[str, Any]:
        async with self._sm() as session:
            repo = ResearchRepository(session)
            ws = await repo.get_workspace(workspace_id=workspace_id, rws_id=rws_id)
            if ws is None:
                raise NotFoundError("Research workspace not found")
            await repo.remove_item(rws_id=rws_id, object_id=object_id)
            await session.commit()
            return {"removed": True}

    async def list_items(
        self, *, workspace_id: uuid.UUID, rws_id: uuid.UUID
    ) -> list[tuple[ResearchWorkspaceItem, IntelligenceObject | None]]:
        async with self._sm() as session:
            repo = ResearchRepository(session)
            ws = await repo.get_workspace(workspace_id=workspace_id, rws_id=rws_id)
            if ws is None:
                raise NotFoundError("Research workspace not found")
            items = await repo.list_items(rws_id)
            object_ids = [i.intelligence_object_id for i in items]
            objects = await repo.get_objects_by_ids(
                workspace_id=workspace_id, ids=object_ids
            )
            by_id = {o.id: o for o in objects}
            return [(i, by_id.get(i.intelligence_object_id)) for i in items]

    # ---------------- packets ----------------

    async def create_packet(
        self,
        *,
        workspace_id: uuid.UUID,
        rws_id: uuid.UUID,
        name: str,
        object_ids: list[uuid.UUID],
    ) -> ResearchPacket:
        async with self._sm() as session:
            repo = ResearchRepository(session)
            ws = await repo.get_workspace(workspace_id=workspace_id, rws_id=rws_id)
            if ws is None:
                raise NotFoundError("Research workspace not found")
            packet = await repo.create_packet(
                rws_id=rws_id,
                workspace_id=workspace_id,
                name=name,
                object_ids=object_ids,
            )
            await session.commit()
            return packet

    async def get_packet(
        self, *, workspace_id: uuid.UUID, packet_id: uuid.UUID
    ) -> ResearchPacket:
        async with self._sm() as session:
            packet = await ResearchRepository(session).get_packet(
                workspace_id=workspace_id, packet_id=packet_id
            )
            if packet is None:
                raise NotFoundError("Research packet not found")
            return packet

    async def list_packets(
        self, *, workspace_id: uuid.UUID, status: str | None
    ) -> list[ResearchPacket]:
        async with self._sm() as session:
            return await ResearchRepository(session).list_packets(
                workspace_id=workspace_id, status=status
            )

    async def check_readiness(
        self, *, workspace_id: uuid.UUID, packet_id: uuid.UUID
    ) -> ReadinessResult:
        async with self._sm() as session:
            return await self._assembler.check_readiness(
                packet_id=packet_id, workspace_id=workspace_id, session=session
            )

    async def mark_ready(
        self, *, workspace_id: uuid.UUID, packet_id: uuid.UUID
    ) -> ResearchPacket:
        async with self._sm() as session:
            repo = ResearchRepository(session)
            packet = await repo.get_packet(
                workspace_id=workspace_id, packet_id=packet_id
            )
            if packet is None:
                raise NotFoundError("Research packet not found")

            readiness = await self._assembler.check_readiness(
                packet_id=packet_id, workspace_id=workspace_id, session=session
            )
            if not readiness.is_ready:
                # Gate enforced at the API layer — not just the mobile UI.
                raise PreconditionFailedError(
                    "Packet has unresolved blockers",
                    details={"blockers": readiness.blockers},
                )

            await repo.mark_ready(packet_id)
            await enqueue_event(
                session,
                name=PACKET_READY,
                payload={
                    "packetId": str(packet_id),
                    "researchWorkspaceId": str(packet.research_workspace_id),
                    "workspaceId": str(workspace_id),
                    "objectCount": len(packet.intelligence_object_ids or []),
                },
                workspace_id=workspace_id,
            )
            await session.commit()
            refreshed = await repo.get_packet(
                workspace_id=workspace_id, packet_id=packet_id
            )
            assert refreshed is not None
            return refreshed

    async def acknowledge_conflict(
        self,
        *,
        workspace_id: uuid.UUID,
        packet_id: uuid.UUID,
        object_id: uuid.UUID,
    ) -> dict[str, Any]:
        async with self._sm() as session:
            repo = ResearchRepository(session)
            packet = await repo.get_packet(
                workspace_id=workspace_id, packet_id=packet_id
            )
            if packet is None:
                raise NotFoundError("Research packet not found")
            await repo.acknowledge_conflict(packet_id=packet_id, object_id=object_id)
            await session.commit()
            return {"packetId": str(packet_id), "acknowledged": str(object_id)}
