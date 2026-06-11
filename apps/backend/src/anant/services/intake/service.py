"""Intake orchestrator — stitches provider output → normalize → dedupe → store → outbox.

Phase 3 Batch 1 ships this file with vendor-agnostic logic only. The vendor
providers (Gmail, RSS, Webhook, API pull) land in Batch 2 and call
`ingest_raw_item()` for every yielded `RawItem`.

Each `ingest_raw_item()` call is its OWN transaction. That's an explicit
choice: a single sync() iteration can yield 100s of items; failing one
should not roll back the rest.

The atomic unit is: { intake_items row + intake_items_normalized row +
intake_dedupe_index row (on first-seen) + outbox_events row } — exactly
the four-write transaction prescribed by ADR-018.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from anant.services.dedupe.fingerprint import compute_fingerprint
from anant.services.dedupe.service import DedupeDecision, DedupeService
from anant.services.intake.providers.base import RawItem
from anant.services.intake.repository import IntakeRepository
from anant.services.normalization.normalizer import normalize_raw_item
from anant.services.queue.outbox import enqueue_event


class IngestOutcome(str, Enum):
    INSERTED = "inserted"
    SKIPPED_PROVIDER_KEY = "skipped_provider_key"
    SKIPPED_FINGERPRINT = "skipped_fingerprint"


@dataclass(frozen=True)
class IngestResult:
    outcome: IngestOutcome
    intake_item_id: uuid.UUID | None
    fingerprint: str
    fingerprint_tier: str


class IntakeService:
    """Stateless, per-request. Compose with a single AsyncSession."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = IntakeRepository(db)
        self.dedupe = DedupeService(db)

    async def ingest_raw_item(
        self,
        *,
        workspace_id: uuid.UUID,
        intake_source_id: uuid.UUID,
        provider_name: str,
        raw: RawItem,
        workspace_tz: str = "UTC",
    ) -> IngestResult:
        # 1. Provider-key dedupe (catches re-ingestion within the same source).
        existing_by_pk = await self.repo.find_existing_by_provider_key(
            workspace_id=workspace_id,
            intake_source_id=intake_source_id,
            external_id=raw.external_id,
        )
        if existing_by_pk is not None:
            return IngestResult(
                outcome=IngestOutcome.SKIPPED_PROVIDER_KEY,
                intake_item_id=existing_by_pk.id,
                fingerprint=existing_by_pk.fingerprint,
                fingerprint_tier="provider_key",
            )

        # 2. Normalize.
        normalized = normalize_raw_item(raw.payload | {
            "sender": raw.sender,
            "subject": raw.subject,
            "body_text": raw.body_text,
            "body_html": raw.body_html,
            "links": [{"url": l.get("url", ""), "anchor": l.get("anchor", "")} for l in raw.links],
        })

        # 3. Two-tier fingerprint (CR-2).
        primary_link = raw.primary_link
        fingerprint, tier = compute_fingerprint(
            sender_domain=normalized.sender_domain,
            subject=normalized.subject,
            primary_link=primary_link,
            received_at=raw.received_at,
            workspace_tz=workspace_tz,
        )

        # 4. Fingerprint dedupe.
        decision = await self.dedupe.decide(
            workspace_id=workspace_id, fingerprint=fingerprint
        )
        if decision.decision == DedupeDecision.SKIP:
            await self.dedupe.record_duplicate(
                workspace_id=workspace_id,
                fingerprint=fingerprint,
                intake_source_id=intake_source_id,
                external_id=raw.external_id,
            )
            await self.repo.write_audit(
                workspace_id=workspace_id,
                intake_source_id=intake_source_id,
                event="dedupe_skip",
                data={
                    "fingerprint": fingerprint,
                    "tier": tier,
                    "first_intake_item_id": str(decision.existing_intake_item_id),
                },
            )
            return IngestResult(
                outcome=IngestOutcome.SKIPPED_FINGERPRINT,
                intake_item_id=decision.existing_intake_item_id,
                fingerprint=fingerprint,
                fingerprint_tier=tier,
            )

        # 5. Insert raw + normalized.
        item = await self.repo.insert_item(
            workspace_id=workspace_id,
            intake_source_id=intake_source_id,
            provider_name=provider_name,
            raw=raw,
            normalized=normalized,
            fingerprint=fingerprint,
        )

        # 6. Record first-seen in dedupe index.
        await self.dedupe.record_first_seen(
            workspace_id=workspace_id,
            fingerprint=fingerprint,
            intake_item_id=item.id,
        )

        # 7. Emit event via outbox (atomic with the inserts above).
        await enqueue_event(
            self.db,
            name="intake.item.received",
            payload={
                "intakeItemId": str(item.id),
                "workspaceId": str(workspace_id),
                "intakeSourceId": str(intake_source_id),
                "providerName": provider_name,
                "receivedAt": raw.received_at.astimezone(UTC).isoformat(),
                "fingerprint": fingerprint,
                "externalId": raw.external_id,
            },
            workspace_id=workspace_id,
        )

        return IngestResult(
            outcome=IngestOutcome.INSERTED,
            intake_item_id=item.id,
            fingerprint=fingerprint,
            fingerprint_tier=tier,
        )

    async def mark_sync_success(
        self,
        *,
        source_id: uuid.UUID,
        new_cursor: dict | None,
    ) -> None:
        await self.repo.update_cursor(
            source_id=source_id,
            cursor=new_cursor,
            last_synced_at=datetime.now(UTC),
        )

    async def mark_sync_failure(
        self,
        *,
        source_id: uuid.UUID,
        error_message: str,
        next_status: str | None,
    ) -> None:
        await self.repo.record_failure(
            source_id=source_id,
            error_message=error_message,
            next_status=next_status,
        )
