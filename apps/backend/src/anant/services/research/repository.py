"""Research repository — DB operations for workspaces, items, and packets."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from anant.core.models import (
    IntelligenceObject,
    ResearchPacket,
    ResearchWorkspace,
    ResearchWorkspaceItem,
)


class ResearchRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ---------------- workspaces ----------------

    async def create_workspace(
        self,
        *,
        account_id: uuid.UUID,
        workspace_id: uuid.UUID,
        name: str,
        description: str | None,
    ) -> ResearchWorkspace:
        row = ResearchWorkspace(
            id=uuid.uuid4(),
            account_id=account_id,
            workspace_id=workspace_id,
            name=name,
            description=description,
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def get_workspace(
        self, *, workspace_id: uuid.UUID, rws_id: uuid.UUID
    ) -> ResearchWorkspace | None:
        result = await self.db.execute(
            select(ResearchWorkspace).where(
                ResearchWorkspace.id == rws_id,
                ResearchWorkspace.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_workspaces(
        self, *, workspace_id: uuid.UUID, account_id: uuid.UUID, status: str = "active"
    ) -> list[ResearchWorkspace]:
        result = await self.db.execute(
            select(ResearchWorkspace)
            .where(
                ResearchWorkspace.workspace_id == workspace_id,
                ResearchWorkspace.account_id == account_id,
                ResearchWorkspace.status == status,
            )
            .order_by(ResearchWorkspace.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_workspace(
        self,
        *,
        rws_id: uuid.UUID,
        name: str | None,
        description: str | None,
        status: str | None,
    ) -> None:
        values: dict[str, object] = {"updated_at": datetime.now(UTC)}
        if name is not None:
            values["name"] = name
        if description is not None:
            values["description"] = description
        if status is not None:
            values["status"] = status
        await self.db.execute(
            update(ResearchWorkspace)
            .where(ResearchWorkspace.id == rws_id)
            .values(**values)
        )

    async def count_active_workspaces(
        self, *, workspace_id: uuid.UUID, account_id: uuid.UUID
    ) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(ResearchWorkspace)
            .where(
                ResearchWorkspace.workspace_id == workspace_id,
                ResearchWorkspace.account_id == account_id,
                ResearchWorkspace.status == "active",
            )
        )
        return int(result.scalar_one() or 0)

    # ---------------- items ----------------

    async def add_item(
        self,
        *,
        rws_id: uuid.UUID,
        object_id: uuid.UUID,
        added_by: uuid.UUID,
        note: str | None,
    ) -> None:
        stmt = (
            pg_insert(ResearchWorkspaceItem)
            .values(
                research_workspace_id=rws_id,
                intelligence_object_id=object_id,
                added_by=added_by,
                note=note,
            )
            .on_conflict_do_update(
                index_elements=["research_workspace_id", "intelligence_object_id"],
                set_={"note": note},
            )
        )
        await self.db.execute(stmt)

    async def remove_item(
        self, *, rws_id: uuid.UUID, object_id: uuid.UUID
    ) -> None:
        item = await self.db.get(ResearchWorkspaceItem, (rws_id, object_id))
        if item is not None:
            await self.db.delete(item)

    async def list_items(
        self, rws_id: uuid.UUID
    ) -> list[ResearchWorkspaceItem]:
        result = await self.db.execute(
            select(ResearchWorkspaceItem)
            .where(ResearchWorkspaceItem.research_workspace_id == rws_id)
            .order_by(ResearchWorkspaceItem.added_at.desc())
        )
        return list(result.scalars().all())

    async def count_items(self, rws_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(ResearchWorkspaceItem)
            .where(ResearchWorkspaceItem.research_workspace_id == rws_id)
        )
        return int(result.scalar_one() or 0)

    # ---------------- packets ----------------

    async def create_packet(
        self,
        *,
        rws_id: uuid.UUID,
        workspace_id: uuid.UUID,
        name: str,
        object_ids: list[uuid.UUID],
    ) -> ResearchPacket:
        row = ResearchPacket(
            id=uuid.uuid4(),
            research_workspace_id=rws_id,
            workspace_id=workspace_id,
            name=name,
            intelligence_object_ids=object_ids,
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def get_packet(
        self, *, workspace_id: uuid.UUID, packet_id: uuid.UUID
    ) -> ResearchPacket | None:
        result = await self.db.execute(
            select(ResearchPacket).where(
                ResearchPacket.id == packet_id,
                ResearchPacket.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_packets(
        self, *, workspace_id: uuid.UUID, status: str | None = None
    ) -> list[ResearchPacket]:
        stmt = select(ResearchPacket).where(
            ResearchPacket.workspace_id == workspace_id
        )
        if status is not None:
            stmt = stmt.where(ResearchPacket.status == status)
        stmt = stmt.order_by(ResearchPacket.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_packets_for_rws(
        self, rws_id: uuid.UUID
    ) -> list[ResearchPacket]:
        result = await self.db.execute(
            select(ResearchPacket)
            .where(ResearchPacket.research_workspace_id == rws_id)
            .order_by(ResearchPacket.created_at.desc())
        )
        return list(result.scalars().all())

    async def mark_ready(self, packet_id: uuid.UUID) -> None:
        await self.db.execute(
            update(ResearchPacket)
            .where(ResearchPacket.id == packet_id)
            .values(status="ready", ready_at=datetime.now(UTC))
        )

    async def acknowledge_conflict(
        self, *, packet_id: uuid.UUID, object_id: uuid.UUID
    ) -> None:
        await self.db.execute(
            update(ResearchPacket)
            .where(ResearchPacket.id == packet_id)
            .values(
                conflict_acknowledged_ids=func.array_append(
                    ResearchPacket.conflict_acknowledged_ids, object_id
                )
            )
        )

    async def count_ready_packets(self, workspace_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(ResearchPacket)
            .where(
                ResearchPacket.workspace_id == workspace_id,
                ResearchPacket.status == "ready",
                ResearchPacket.consumed_at.is_(None),
            )
        )
        return int(result.scalar_one() or 0)

    # ---------------- objects (cross-domain read) ----------------

    async def get_objects_by_ids(
        self, *, workspace_id: uuid.UUID, ids: list[uuid.UUID]
    ) -> list[IntelligenceObject]:
        if not ids:
            return []
        result = await self.db.execute(
            select(IntelligenceObject).where(
                IntelligenceObject.workspace_id == workspace_id,
                IntelligenceObject.id.in_(ids),
            )
        )
        return list(result.scalars().all())
