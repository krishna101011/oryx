"""Intelligence repository — DB operations for intelligence_objects."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.core.models import (
    Claim,
    IntelligenceObject,
    VerificationAuditLog,
    VerificationRun,
    Workspace,
)
from oryx.services.intelligence.models import IntelligenceObjectResult

# Analyst decisions are sticky: a recompose must not overwrite them.
STICKY_STATUSES = ("analyst_approved", "analyst_rejected")
TERMINAL_RUN_STATUSES = ("complete", "failed")


class IntelligenceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def workspace_exists(self, workspace_id: uuid.UUID) -> bool:
        row = await self.db.get(Workspace, workspace_id)
        return row is not None and row.deleted_at is None

    # ---------------- terminal-state gate ----------------

    async def all_claims_for_item(
        self, *, workspace_id: uuid.UUID, intake_item_id: uuid.UUID
    ) -> list[Claim]:
        result = await self.db.execute(
            select(Claim).where(
                Claim.workspace_id == workspace_id,
                Claim.intake_item_id == intake_item_id,
            )
        )
        return list(result.scalars().all())

    async def terminal_claim_ids(self, claim_ids: list[uuid.UUID]) -> set[uuid.UUID]:
        """Of the given claims, those with a complete OR failed verification run."""
        if not claim_ids:
            return set()
        result = await self.db.execute(
            select(VerificationRun.claim_id)
            .where(
                VerificationRun.claim_id.in_(claim_ids),
                VerificationRun.status.in_(TERMINAL_RUN_STATUSES),
            )
            .distinct()
        )
        return {row[0] for row in result.all()}

    # ---------------- objects ----------------

    async def get_object(
        self, *, workspace_id: uuid.UUID, object_id: uuid.UUID
    ) -> IntelligenceObject | None:
        result = await self.db.execute(
            select(IntelligenceObject).where(
                IntelligenceObject.id == object_id,
                IntelligenceObject.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_object_by_item(
        self, *, workspace_id: uuid.UUID, intake_item_id: uuid.UUID
    ) -> IntelligenceObject | None:
        result = await self.db.execute(
            select(IntelligenceObject).where(
                IntelligenceObject.workspace_id == workspace_id,
                IntelligenceObject.intake_item_id == intake_item_id,
            )
        )
        return result.scalar_one_or_none()

    async def objects_for_item(
        self, *, workspace_id: uuid.UUID, intake_item_id: uuid.UUID
    ) -> list[IntelligenceObject]:
        result = await self.db.execute(
            select(IntelligenceObject).where(
                IntelligenceObject.workspace_id == workspace_id,
                IntelligenceObject.intake_item_id == intake_item_id,
            )
        )
        return list(result.scalars().all())

    async def insert_object(
        self,
        *,
        workspace_id: uuid.UUID,
        intake_item_id: uuid.UUID,
        result: IntelligenceObjectResult,
    ) -> IntelligenceObject | None:
        """Create the object. ON CONFLICT DO NOTHING — a concurrent insert wins
        and we return None (caller treats as already-composed)."""
        stmt = (
            pg_insert(IntelligenceObject)
            .values(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                intake_item_id=intake_item_id,
                epistemic_type=result.epistemic_type,
                confidence_score=result.confidence_score,
                verification_status=result.verification_status,
                claim_ids=result.claim_ids,
                conflict_ids=result.conflict_ids,
                key_facts=result.key_facts,
                headline=result.headline,
                scoring_version=result.scoring_version,
            )
            .on_conflict_do_nothing(
                index_elements=["workspace_id", "intake_item_id"]
            )
            .returning(IntelligenceObject.id)
        )
        new_id = (await self.db.execute(stmt)).scalar_one_or_none()
        if new_id is None:
            return None
        return await self.db.get(IntelligenceObject, new_id)

    async def apply_composition(
        self,
        *,
        object_id: uuid.UUID,
        result: IntelligenceObjectResult,
        status: str,
    ) -> None:
        """Refresh a recomposed object. `status` lets the caller keep a sticky
        analyst status instead of the freshly composed one."""
        await self.db.execute(
            update(IntelligenceObject)
            .where(IntelligenceObject.id == object_id)
            .values(
                epistemic_type=result.epistemic_type,
                confidence_score=result.confidence_score,
                verification_status=status,
                claim_ids=result.claim_ids,
                conflict_ids=result.conflict_ids,
                key_facts=result.key_facts,
                headline=result.headline,
                scoring_version=result.scoring_version,
                updated_at=datetime.now(UTC),
            )
        )

    async def set_status(self, *, object_id: uuid.UUID, status: str) -> None:
        await self.db.execute(
            update(IntelligenceObject)
            .where(IntelligenceObject.id == object_id)
            .values(verification_status=status, updated_at=datetime.now(UTC))
        )

    async def list_objects(
        self,
        *,
        workspace_id: uuid.UUID,
        status: str | None = None,
        min_score: float | None = None,
        epistemic_type: str | None = None,
        search: str | None = None,
        limit: int = 50,
    ) -> list[IntelligenceObject]:
        stmt = select(IntelligenceObject).where(
            IntelligenceObject.workspace_id == workspace_id
        )
        if status is not None:
            stmt = stmt.where(IntelligenceObject.verification_status == status)
        if epistemic_type is not None:
            stmt = stmt.where(IntelligenceObject.epistemic_type == epistemic_type)
        if min_score is not None:
            stmt = stmt.where(IntelligenceObject.confidence_score >= min_score)
        if search:
            stmt = stmt.where(
                text(
                    "to_tsvector('english', headline) "
                    "@@ plainto_tsquery('english', :q)"
                ).bindparams(q=search)
            )
        stmt = stmt.order_by(IntelligenceObject.created_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ---------------- /me counts ----------------

    async def count_objects(self, workspace_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(IntelligenceObject)
            .where(IntelligenceObject.workspace_id == workspace_id)
        )
        return int(result.scalar_one() or 0)

    # ---------------- audit ----------------

    async def write_audit(
        self,
        *,
        workspace_id: uuid.UUID,
        account_id: uuid.UUID | None,
        event: str,
        entity_id: uuid.UUID,
        data: dict[str, Any] | None = None,
    ) -> None:
        self.db.add(
            VerificationAuditLog(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                account_id=account_id,
                event=event,
                entity_type="intelligence_object",
                entity_id=entity_id,
                data=data or {},
            )
        )
