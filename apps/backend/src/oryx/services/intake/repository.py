"""Intake repository — intake_sources + intake_items + intake_items_normalized.

Service-level orchestration lives in service.py; storage primitives live
here. Every method scopes by workspace_id; no global queries.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.core.models import (
    IntakeAuditLog,
    IntakeItem,
    IntakeItemNormalized,
    IntakeSource,
)
from oryx.services.intake.providers.base import RawItem
from oryx.services.normalization.normalizer import NormalizedItem


class IntakeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ---------------- sources ----------------
    async def get_source(
        self, *, workspace_id: uuid.UUID, source_id: uuid.UUID
    ) -> IntakeSource | None:
        result = await self.db.execute(
            select(IntakeSource).where(
                IntakeSource.id == source_id,
                IntakeSource.workspace_id == workspace_id,
                IntakeSource.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def update_cursor(
        self,
        *,
        source_id: uuid.UUID,
        cursor: dict[str, Any] | None,
        last_synced_at: datetime,
    ) -> None:
        await self.db.execute(
            update(IntakeSource)
            .where(IntakeSource.id == source_id)
            .values(
                cursor=cursor,
                last_synced_at=last_synced_at,
                last_attempt_at=last_synced_at,
                consecutive_failures=0,
                status="healthy",
                last_error=None,
                updated_at=datetime.now(UTC),
            )
        )

    async def record_failure(
        self,
        *,
        source_id: uuid.UUID,
        error_message: str,
        next_status: str | None,
    ) -> None:
        now = datetime.now(UTC)
        values: dict[str, Any] = {
            "consecutive_failures": IntakeSource.consecutive_failures + 1,
            "last_attempt_at": now,
            "last_error": error_message,
            "updated_at": now,
        }
        if next_status is not None:
            values["status"] = next_status
        await self.db.execute(
            update(IntakeSource).where(IntakeSource.id == source_id).values(**values)
        )

    # ---------------- items ----------------
    async def find_existing_by_provider_key(
        self,
        *,
        workspace_id: uuid.UUID,
        intake_source_id: uuid.UUID,
        external_id: str,
    ) -> IntakeItem | None:
        result = await self.db.execute(
            select(IntakeItem).where(
                IntakeItem.workspace_id == workspace_id,
                IntakeItem.intake_source_id == intake_source_id,
                IntakeItem.external_id == external_id,
            )
        )
        return result.scalar_one_or_none()

    async def insert_item(
        self,
        *,
        workspace_id: uuid.UUID,
        intake_source_id: uuid.UUID,
        provider_name: str,
        raw: RawItem,
        normalized: NormalizedItem,
        fingerprint: str,
    ) -> IntakeItem:
        item = IntakeItem(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            intake_source_id=intake_source_id,
            provider_name=provider_name,
            external_id=raw.external_id,
            received_at=raw.received_at,
            payload=raw.payload,
            fingerprint=fingerprint,
        )
        self.db.add(item)
        await self.db.flush()

        norm = IntakeItemNormalized(
            intake_item_id=item.id,
            sender_domain=normalized.sender_domain,
            sender_label=normalized.sender_label,
            subject=normalized.subject,
            body_text=normalized.body_text,
            links=normalized.links,
            item_metadata=normalized.metadata,
            normalizer_version=normalized.normalizer_version,
        )
        self.db.add(norm)
        await self.db.flush()
        return item

    # ---------------- audit ----------------
    async def write_audit(
        self,
        *,
        workspace_id: uuid.UUID,
        intake_source_id: uuid.UUID | None,
        event: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        row = IntakeAuditLog(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            intake_source_id=intake_source_id,
            event=event,
            data=data or {},
        )
        self.db.add(row)
