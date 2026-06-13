"""Review repository — analyst_reviews writes + claim existence reads.

Conflict-record mutations and the review-queue reads are owned by
ConflictRepository; this module owns only the append-only analyst_reviews
log (overrides are recorded here, never as mutations of the source rows).
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from anant.core.models import AnalystReview, Claim


class ReviewRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_claim(
        self, *, workspace_id: uuid.UUID, claim_id: uuid.UUID
    ) -> Claim | None:
        result = await self.db.execute(
            select(Claim).where(
                Claim.id == claim_id, Claim.workspace_id == workspace_id
            )
        )
        return result.scalar_one_or_none()

    async def insert_review(
        self,
        *,
        account_id: uuid.UUID,
        workspace_id: uuid.UUID,
        entity_type: str,
        entity_id: uuid.UUID,
        outcome: str,
        note: str,
    ) -> AnalystReview:
        row = AnalystReview(
            id=uuid.uuid4(),
            account_id=account_id,
            workspace_id=workspace_id,
            entity_type=entity_type,
            entity_id=entity_id,
            outcome=outcome,
            note=note,
        )
        self.db.add(row)
        await self.db.flush()
        return row
