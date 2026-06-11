"""Workspace deletion cascade for intake data — CR-6 (§17.2).

Called by the (future, compliance-phase) workspace deletion flow, and
runnable by an operator:

    python -m anant.services.intake.workspace_cascade <workspace_id>

Order, exactly as frozen:

    emit workspace.deletion.started
      → disable every intake source
      → best-effort upstream credential revoke (failure → orphan table)
      → delete intake_credentials, intake_sources
      → delete item-side rows (dedupe children first, FK order)
      → delete webhook_idempotency_keys, outbox_events
    emit workspace.deletion.completed

Idempotent: every statement is a workspace-scoped delete/update; a re-run
on an already-purged workspace deletes nothing and still emits the
completion event with zero counts.

The two lifecycle events are emitted as PLATFORM events (workspaceId null
in the envelope's routing column, the id carried in the payload) — a row
with workspace_id = X would be reaped by this very cascade's outbox
delete, per the frozen §17.2 delete list.
"""
from __future__ import annotations

import asyncio
import sys
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from anant.core.logging import get_logger
from anant.core.models import (
    IntakeAuditLog,
    IntakeCredentials,
    IntakeDedupeIndex,
    IntakeItem,
    IntakeItemDuplicate,
    IntakeItemNormalized,
    IntakeSource,
    OutboxEvent,
    WebhookIdempotencyKey,
    WorkspaceDeletionOrphanCredential,
)
from anant.services.intake.credentials import IntakeCredentialsRepository
from anant.services.intake.providers.gmail import auth as gmail_auth
from anant.services.queue.outbox import enqueue_event

logger = get_logger(__name__)

# Async revoke hook: (provider_kind, decrypted_refresh_or_access_token) → success.
RevokeFn = Callable[[str, str], Awaitable[bool]]


@dataclass(frozen=True)
class CascadeReport:
    workspace_id: uuid.UUID
    sources_deleted: int
    credentials_deleted: int
    revoke_failures: int
    items_deleted: int
    outbox_deleted: int
    idempotency_keys_deleted: int


def _rowcount(result: object) -> int:
    return int(getattr(result, "rowcount", 0) or 0)


async def _default_revoke(provider_kind: str, token: str) -> bool:
    """Gmail is the only Phase 3 vendor with a revocable upstream grant.

    API-pull bearer/api-key credentials have no standard revoke endpoint;
    webhook sources hold no upstream grant at all. Both count as success —
    there is nothing upstream to orphan.
    """
    if provider_kind == "gmail":
        return await gmail_auth.revoke_token(token)
    return True


async def cascade_workspace_intake_deletion(
    sm: async_sessionmaker[AsyncSession],
    workspace_id: uuid.UUID,
    *,
    revoke: RevokeFn | None = None,
) -> CascadeReport:
    revoke = revoke or _default_revoke

    async with sm() as session:
        await enqueue_event(
            session,
            name="workspace.deletion.started",
            payload={"workspaceId": str(workspace_id)},
            workspace_id=None,
        )
        await session.commit()

    revoke_failures = 0
    async with sm() as session:
        result = await session.execute(
            select(IntakeSource).where(IntakeSource.workspace_id == workspace_id)
        )
        sources = list(result.scalars().all())

        # Disable first so the scheduler stops picking these up while the
        # rest of the cascade runs.
        await session.execute(
            update(IntakeSource)
            .where(IntakeSource.workspace_id == workspace_id)
            .values(enabled=False, status="disabled")
        )
        await session.commit()

        creds_repo = IntakeCredentialsRepository(session)
        for src in sources:
            pair = await creds_repo.load(
                intake_source_id=src.id, workspace_id=workspace_id
            )
            if pair is None:
                continue
            token = (pair.refresh_token or pair.token).decode("utf-8")
            try:
                ok = await revoke(src.kind, token)
            except Exception as e:
                ok = False
                logger.warning(
                    "cascade.revoke_raised",
                    extra={"intake_source_id": str(src.id), "error_class": type(e).__name__},
                )
            if not ok:
                revoke_failures += 1
                session.add(
                    WorkspaceDeletionOrphanCredential(
                        id=uuid.uuid4(),
                        workspace_id=workspace_id,
                        intake_source_id=src.id,
                        provider_kind=src.kind,
                        detail="upstream revoke failed; local credentials deleted",
                    )
                )
        await session.commit()

    counts: dict[str, int] = {}
    async with sm() as session:
        # FK-safe order: children of intake_items first, then items, then
        # credentials before sources, then the workspace-scoped queues.
        item_ids = select(IntakeItem.id).where(IntakeItem.workspace_id == workspace_id)
        await session.execute(
            delete(IntakeItemNormalized).where(
                IntakeItemNormalized.intake_item_id.in_(item_ids)
            )
        )
        await session.execute(
            delete(IntakeItemDuplicate).where(
                IntakeItemDuplicate.workspace_id == workspace_id
            )
        )
        await session.execute(
            delete(IntakeDedupeIndex).where(
                IntakeDedupeIndex.workspace_id == workspace_id
            )
        )
        res_items = await session.execute(
            delete(IntakeItem).where(IntakeItem.workspace_id == workspace_id)
        )
        counts["items"] = _rowcount(res_items)

        res_creds = await session.execute(
            delete(IntakeCredentials).where(
                IntakeCredentials.workspace_id == workspace_id
            )
        )
        counts["credentials"] = _rowcount(res_creds)

        await session.execute(
            delete(IntakeAuditLog).where(IntakeAuditLog.workspace_id == workspace_id)
        )
        res_sources = await session.execute(
            delete(IntakeSource).where(IntakeSource.workspace_id == workspace_id)
        )
        counts["sources"] = _rowcount(res_sources)

        res_keys = await session.execute(
            delete(WebhookIdempotencyKey).where(
                WebhookIdempotencyKey.workspace_id == workspace_id
            )
        )
        counts["idempotency_keys"] = _rowcount(res_keys)

        res_outbox = await session.execute(
            delete(OutboxEvent).where(OutboxEvent.workspace_id == workspace_id)
        )
        counts["outbox"] = _rowcount(res_outbox)
        await session.commit()

    async with sm() as session:
        await enqueue_event(
            session,
            name="workspace.deletion.completed",
            payload={
                "workspaceId": str(workspace_id),
                "sourcesDeleted": counts["sources"],
                "itemsDeleted": counts["items"],
                "revokeFailures": revoke_failures,
            },
            workspace_id=None,
        )
        await session.commit()

    report = CascadeReport(
        workspace_id=workspace_id,
        sources_deleted=counts["sources"],
        credentials_deleted=counts["credentials"],
        revoke_failures=revoke_failures,
        items_deleted=counts["items"],
        outbox_deleted=counts["outbox"],
        idempotency_keys_deleted=counts["idempotency_keys"],
    )
    logger.info(
        "cascade.completed",
        extra={"workspace_id": str(workspace_id), "sources": report.sources_deleted,
               "items": report.items_deleted, "revoke_failures": revoke_failures},
    )
    return report


async def _amain(workspace_id: str) -> None:
    from anant.core.db import get_sessionmaker
    from anant.core.logging import configure_logging

    configure_logging()
    report = await cascade_workspace_intake_deletion(
        get_sessionmaker(), uuid.UUID(workspace_id)
    )
    print(report)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m anant.services.intake.workspace_cascade <workspace_id>")
    asyncio.run(_amain(sys.argv[1]))
