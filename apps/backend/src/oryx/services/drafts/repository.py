"""Drafts repository — DB operations only, no business rules.

Owns: content_drafts, draft_versions, draft_citations, and the AI budget ledger
reads/writes the drafts service needs. The ONLY write it makes to a Phase 4 table
is research_packets.consumed_at (the Phase 5 handoff marker).
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.core.models import (
    ContentDraft,
    DraftCitation,
    DraftVersion,
    IntelligenceObject,
    ResearchPacket,
    Workspace,
    WorkspaceAIBudget,
)

# Matches the workspace_ai_budget column default (migration 0004).
DEFAULT_BUDGET_LIMIT = 100_000


class DraftsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ---------------- workspace + packet (Phase 4 reads) ----------------

    async def workspace_exists(self, workspace_id: uuid.UUID) -> bool:
        row = await self.db.get(Workspace, workspace_id)
        return row is not None and row.deleted_at is None

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

    async def mark_packet_consumed(self, packet_id: uuid.UUID) -> None:
        """Set consumed_at (the ONLY write Phase 5 makes to a Phase 4 table).
        Idempotent: the WHERE clause no-ops once consumed_at is set. Status is
        left untouched — the blueprint mandates consumed_at and nothing else."""
        await self.db.execute(
            update(ResearchPacket)
            .where(
                ResearchPacket.id == packet_id,
                ResearchPacket.consumed_at.is_(None),
            )
            .values(consumed_at=datetime.now(UTC))
        )

    async def get_objects(
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
        rows = {r.id: r for r in result.scalars().all()}
        # Preserve the packet's object ordering.
        return [rows[i] for i in ids if i in rows]

    # ---------------- drafts ----------------

    async def get_draft(
        self, *, workspace_id: uuid.UUID, draft_id: uuid.UUID
    ) -> ContentDraft | None:
        result = await self.db.execute(
            select(ContentDraft).where(
                ContentDraft.id == draft_id,
                ContentDraft.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_draft_by_packet(
        self, *, workspace_id: uuid.UUID, packet_id: uuid.UUID
    ) -> ContentDraft | None:
        result = await self.db.execute(
            select(ContentDraft).where(
                ContentDraft.workspace_id == workspace_id,
                ContentDraft.packet_id == packet_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_draft(
        self,
        *,
        workspace_id: uuid.UUID,
        account_id: uuid.UUID,
        packet_id: uuid.UUID,
        format: str,
        title: str,
        generation_model: str,
        generation_version: int,
        word_count: int | None,
    ) -> ContentDraft | None:
        """Insert the draft. ON CONFLICT (workspace_id, packet_id) DO NOTHING —
        a concurrent generate wins and we return None (one draft per packet)."""
        stmt = (
            pg_insert(ContentDraft)
            .values(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                account_id=account_id,
                packet_id=packet_id,
                format=format,
                title=title,
                status="draft",
                current_version=1,
                generation_model=generation_model,
                generation_version=generation_version,
                word_count=word_count,
            )
            .on_conflict_do_nothing(constraint="uq_content_drafts_packet")
            .returning(ContentDraft.id)
        )
        new_id = (await self.db.execute(stmt)).scalar_one_or_none()
        if new_id is None:
            return None
        return await self.db.get(ContentDraft, new_id)

    async def list_drafts(
        self,
        *,
        workspace_id: uuid.UUID,
        status: str | None = None,
        packet_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> list[ContentDraft]:
        stmt = select(ContentDraft).where(ContentDraft.workspace_id == workspace_id)
        if status is not None:
            stmt = stmt.where(ContentDraft.status == status)
        if packet_id is not None:
            stmt = stmt.where(ContentDraft.packet_id == packet_id)
        stmt = stmt.order_by(ContentDraft.created_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def set_current_version(
        self, *, draft_id: uuid.UUID, version_number: int, word_count: int | None
    ) -> None:
        await self.db.execute(
            update(ContentDraft)
            .where(ContentDraft.id == draft_id)
            .values(
                current_version=version_number,
                word_count=word_count,
                updated_at=datetime.now(UTC),
            )
        )

    # ---------------- versions (append-only) ----------------

    async def max_version_number(self, draft_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.max(DraftVersion.version_number)).where(
                DraftVersion.draft_id == draft_id
            )
        )
        return int(result.scalar_one() or 0)

    async def insert_version(
        self,
        *,
        draft_id: uuid.UUID,
        version_number: int,
        content: str,
        edited_by: uuid.UUID,
        is_ai_generated: bool,
        content_html: str | None = None,
        edit_note: str | None = None,
        word_count: int | None = None,
        token_count: int | None = None,
    ) -> DraftVersion:
        row = DraftVersion(
            id=uuid.uuid4(),
            draft_id=draft_id,
            version_number=version_number,
            content=content,
            content_html=content_html,
            edited_by=edited_by,
            edit_note=edit_note,
            word_count=word_count,
            token_count=token_count,
            is_ai_generated=is_ai_generated,
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def list_versions(self, draft_id: uuid.UUID) -> list[DraftVersion]:
        result = await self.db.execute(
            select(DraftVersion)
            .where(DraftVersion.draft_id == draft_id)
            .order_by(DraftVersion.version_number.desc())
        )
        return list(result.scalars().all())

    async def get_version(
        self, *, draft_id: uuid.UUID, version_number: int
    ) -> DraftVersion | None:
        result = await self.db.execute(
            select(DraftVersion).where(
                DraftVersion.draft_id == draft_id,
                DraftVersion.version_number == version_number,
            )
        )
        return result.scalar_one_or_none()

    # ---------------- citations ----------------

    async def insert_citations(
        self, *, draft_id: uuid.UUID, object_ids: list[uuid.UUID]
    ) -> None:
        for object_id in object_ids:
            stmt = (
                pg_insert(DraftCitation)
                .values(draft_id=draft_id, intelligence_object_id=object_id)
                .on_conflict_do_nothing()
            )
            await self.db.execute(stmt)

    async def list_citation_object_ids(self, draft_id: uuid.UUID) -> list[uuid.UUID]:
        result = await self.db.execute(
            select(DraftCitation.intelligence_object_id)
            .where(DraftCitation.draft_id == draft_id)
            .order_by(DraftCitation.added_at)
        )
        return [row[0] for row in result.all()]

    # ---------------- AI budget ledger ----------------

    async def budget_remaining(self, workspace_id: uuid.UUID) -> int:
        today = datetime.now(UTC).date()
        result = await self.db.execute(
            select(
                WorkspaceAIBudget.tokens_used, WorkspaceAIBudget.budget_limit
            ).where(
                WorkspaceAIBudget.workspace_id == workspace_id,
                WorkspaceAIBudget.budget_date == today,
            )
        )
        row = result.one_or_none()
        if row is None:
            return DEFAULT_BUDGET_LIMIT
        used, limit = row
        return max(0, int(limit) - int(used))

    async def add_tokens_used(self, workspace_id: uuid.UUID, tokens: int) -> None:
        today = datetime.now(UTC).date()
        stmt = (
            pg_insert(WorkspaceAIBudget)
            .values(
                workspace_id=workspace_id,
                budget_date=today,
                tokens_used=tokens,
            )
            .on_conflict_do_update(
                index_elements=["workspace_id", "budget_date"],
                set_={
                    "tokens_used": WorkspaceAIBudget.tokens_used + tokens,
                    "updated_at": func.now(),
                },
            )
        )
        await self.db.execute(stmt)
