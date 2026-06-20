"""Dedupe decision service.

Given the (workspace_id, fingerprint) pair, return either:
  - DedupeDecision.INSERT — first time seen; caller proceeds with full insert
  - DedupeDecision.SKIP   — duplicate; caller MUST NOT insert intake_items row

Provider-key check is done at the intake repository level (UNIQUE on
(workspace_id, intake_source_id, external_id)). This service handles the
cross-source content-fingerprint case.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from oryx.services.dedupe.repository import DedupeRepository


class DedupeDecision(str, Enum):
    INSERT = "insert"
    SKIP = "skip"


@dataclass(frozen=True)
class DedupeOutcome:
    decision: DedupeDecision
    existing_intake_item_id: uuid.UUID | None


class DedupeService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = DedupeRepository(db)

    async def decide(
        self, *, workspace_id: uuid.UUID, fingerprint: str
    ) -> DedupeOutcome:
        existing = await self.repo.get_index(
            workspace_id=workspace_id, fingerprint=fingerprint
        )
        if existing is None:
            return DedupeOutcome(
                decision=DedupeDecision.INSERT,
                existing_intake_item_id=None,
            )
        return DedupeOutcome(
            decision=DedupeDecision.SKIP,
            existing_intake_item_id=existing.first_intake_item_id,
        )

    async def record_first_seen(
        self,
        *,
        workspace_id: uuid.UUID,
        fingerprint: str,
        intake_item_id: uuid.UUID,
    ) -> None:
        await self.repo.insert_first_seen(
            workspace_id=workspace_id,
            fingerprint=fingerprint,
            intake_item_id=intake_item_id,
        )

    async def record_duplicate(
        self,
        *,
        workspace_id: uuid.UUID,
        fingerprint: str,
        intake_source_id: uuid.UUID,
        external_id: str,
    ) -> None:
        await self.repo.record_duplicate(
            workspace_id=workspace_id,
            fingerprint=fingerprint,
            intake_source_id=intake_source_id,
            external_id=external_id,
        )
