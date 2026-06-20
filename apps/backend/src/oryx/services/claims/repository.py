"""Claims repository — DB operations only, no business rules.

Owns: claims rows, the workspace_ai_budget ledger, and the reads the
service layer needs from Phase 3 tables (normalized items, workspaces).
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.core.models import (
    Claim,
    IntakeItemNormalized,
    Workspace,
    WorkspaceAIBudget,
)

# Default daily token allowance when no ledger row exists yet — matches the
# column default in migration 0004.
DEFAULT_BUDGET_LIMIT = 100_000


class ClaimsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ---------------- reads from Phase 3 tables ----------------

    async def workspace_exists(self, workspace_id: uuid.UUID) -> bool:
        row = await self.db.get(Workspace, workspace_id)
        return row is not None and row.deleted_at is None

    async def get_normalized_item(
        self, intake_item_id: uuid.UUID
    ) -> IntakeItemNormalized | None:
        return await self.db.get(IntakeItemNormalized, intake_item_id)

    # ---------------- claims ----------------

    async def insert_claim(
        self,
        *,
        workspace_id: uuid.UUID,
        intake_item_id: uuid.UUID,
        text: str,
        subject: str,
        predicate: str,
        object_: str | None,
        extractor_version: int,
        requires_analyst_review: bool = False,
    ) -> uuid.UUID | None:
        """Insert one claim; returns its id, or None when the idempotency
        guard (workspace, item, text) made the insert a silent no-op."""
        stmt = (
            pg_insert(Claim)
            .values(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                intake_item_id=intake_item_id,
                text=text,
                subject=subject,
                predicate=predicate,
                object=object_,
                epistemic_type="unclassified",
                extractor_version=extractor_version,
                requires_analyst_review=requires_analyst_review,
            )
            .on_conflict_do_nothing(constraint="uq_claims_workspace_item_text")
            .returning(Claim.id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_claims_for_item(
        self, *, workspace_id: uuid.UUID, intake_item_id: uuid.UUID
    ) -> list[Claim]:
        result = await self.db.execute(
            select(Claim).where(
                Claim.workspace_id == workspace_id,
                Claim.intake_item_id == intake_item_id,
            )
        )
        return list(result.scalars().all())

    async def get_claim(
        self, *, workspace_id: uuid.UUID, claim_id: uuid.UUID
    ) -> Claim | None:
        result = await self.db.execute(
            select(Claim).where(
                Claim.id == claim_id, Claim.workspace_id == workspace_id
            )
        )
        return result.scalar_one_or_none()

    async def set_epistemic_type(
        self,
        *,
        claim_id: uuid.UUID,
        epistemic_type: str,
        classifier_version: int,
        requires_analyst_review: bool,
    ) -> None:
        await self.db.execute(
            update(Claim)
            .where(Claim.id == claim_id)
            .values(
                epistemic_type=epistemic_type,
                classifier_version=classifier_version,
                requires_analyst_review=requires_analyst_review,
            )
        )

    async def flag_for_review(self, claim_id: uuid.UUID) -> None:
        """Mark a claim for analyst attention without touching its typing
        state (used when the AI budget blocks classification)."""
        await self.db.execute(
            update(Claim)
            .where(Claim.id == claim_id)
            .values(requires_analyst_review=True)
        )

    # ---------------- AI budget ledger ----------------

    async def budget_remaining(self, workspace_id: uuid.UUID) -> int:
        """Tokens left for today; DEFAULT_BUDGET_LIMIT when no row yet."""
        today = datetime.now(UTC).date()
        result = await self.db.execute(
            select(WorkspaceAIBudget.tokens_used, WorkspaceAIBudget.budget_limit).where(
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
        """Upsert today's ledger row (ON CONFLICT DO UPDATE)."""
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
