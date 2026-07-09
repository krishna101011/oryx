"""Publishing engine (§12.2 / §16) — fan-out delivery of an approved draft.

publish_draft delivers one draft's current version to one or more targets. Each
target is INDEPENDENT: its DB writes form their own atomic unit, so one target's
failure never rolls back another's success (§16.1). The adapter network call
happens OUTSIDE any transaction (mirrors the drafts service's AI-call shape).

Idempotency (§16.2): before delivering, a 'delivered' publication for
(draft, version, target) short-circuits — the adapter is not called again. The
pending row is inserted ON CONFLICT DO NOTHING against
uq_publications_draft_version_target, so concurrent calls converge on one row.

Retry (§16.3): PermanentChannelError → 'failed' immediately, no retry.
TransientChannelError → attempt_count incremented; below MAX_PUBLISH_ATTEMPTS the
row stays 'pending' for the outbox/drainer retry mechanism to re-drive (we do NOT
build a second retry loop here); at the ceiling it becomes 'failed'.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from oryx.core.errors import NotFoundError, PreconditionFailedError
from oryx.core.logging import get_logger
from oryx.services.drafts.events.constants import DRAFT_APPROVED
from oryx.services.drafts.repository import DraftsRepository
from oryx.services.publishing.channels.base import (
    PermanentChannelError,
    TransientChannelError,
)
from oryx.services.publishing.channels.registry import get_channel
from oryx.services.publishing.citations import (
    CitationSummary,
    format_citation_footer,
    load_draft_citations,
    snapshot_citations,
)
from oryx.services.publishing.events.constants import (
    CONTENT_PUBLISH_FAILED,
    CONTENT_PUBLISHED,
)
from oryx.services.publishing.repository import PublicationsRepository
from oryx.services.queue.outbox import enqueue_event
from oryx.services.targets.repository import TargetsRepository

logger = get_logger(__name__)

# Outer attempt ceiling for transient failures (§16.3). The webhook adapter does
# its own 3 internal retries first; this counts engine-level attempts.
MAX_PUBLISH_ATTEMPTS = 5


@dataclass(frozen=True)
class TargetResult:
    target_id: uuid.UUID
    publication_id: uuid.UUID | None
    status: str  # 'delivered' | 'failed' | 'pending' | 'skipped'
    external_id: str | None = None
    external_url: str | None = None
    error_message: str | None = None


class PublishingEngine:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def publish_draft(
        self,
        *,
        draft_id: uuid.UUID,
        target_ids: list[uuid.UUID],
        workspace_id: uuid.UUID,
        account_id: uuid.UUID,
        correlation_id: str | None = None,
    ) -> list[TargetResult]:
        # ---- 1+2. Load draft (must be approved) + current version content ----
        async with self._sm() as session:
            repo = DraftsRepository(session)
            draft = await repo.get_draft(
                workspace_id=workspace_id, draft_id=draft_id
            )
            if draft is None:
                raise NotFoundError("Draft not found")
            if draft.status not in ("approved", "published", "scheduled"):
                # 'published' is allowed so re-publishing to a NEW target after a
                # prior partial success still works (idempotency guards the rest).
                # 'scheduled' (Wave E) is allowed because the calendar scheduler
                # fires drafts that scheduling has already promoted to
                # 'scheduled'; a successful delivery still moves them to
                # 'published' below.
                raise PreconditionFailedError(
                    "Only an approved draft can be published",
                    details={"status": draft.status},
                )
            version_number = draft.current_version
            version = await repo.get_version(
                draft_id=draft_id, version_number=version_number
            )
            if version is None:
                raise PreconditionFailedError(
                    "Draft has no current version content"
                )
            content = version.content
            draft_title = draft.title
            # Provenance (post-freeze citation patch): load ONCE per publish call,
            # not per target — citations don't vary by target. Zero citations is
            # handled gracefully downstream (empty footer / empty webhook array).
            citations = await load_draft_citations(draft_id, session)
            # Causation parent for content.published (§8.2): the approval event.
            causation_id = await repo.latest_event_id_for_draft(
                draft_id, (DRAFT_APPROVED,)
            )

        # ---- 3. Fan-out: each target independent ----
        results: list[TargetResult] = []
        for target_id in target_ids:
            results.append(
                await self._publish_one(
                    draft_id=draft_id,
                    version_number=version_number,
                    content=content,
                    citations=citations,
                    draft_title=draft_title,
                    target_id=target_id,
                    workspace_id=workspace_id,
                    account_id=account_id,
                    causation_id=causation_id,
                    correlation_id=correlation_id,
                )
            )

        # ---- 4. Draft status: published if AT LEAST ONE target delivered ----
        if any(r.status == "delivered" for r in results):
            async with self._sm() as session:
                repo = DraftsRepository(session)
                fresh = await repo.get_draft(
                    workspace_id=workspace_id, draft_id=draft_id
                )
                if fresh is not None and fresh.status != "published":
                    await repo.set_draft_status(
                        draft_id=draft_id, status="published"
                    )
                    await self._mark_draft_published_at(session, draft_id)
                    await session.commit()

        # ---- 5. Per-target results for the API response ----
        return results

    async def _publish_one(
        self,
        *,
        draft_id: uuid.UUID,
        version_number: int,
        content: str,
        citations: list[CitationSummary],
        draft_title: str,
        target_id: uuid.UUID,
        workspace_id: uuid.UUID,
        account_id: uuid.UUID,
        causation_id: str | None,
        correlation_id: str | None,
    ) -> TargetResult:
        # --- a+b+c. Idempotency check, load+decrypt target, ensure pending row ---
        async with self._sm() as session:
            pubs = PublicationsRepository(session)
            targets = TargetsRepository(session)

            existing = await pubs.get(
                draft_id=draft_id,
                version_number=version_number,
                target_id=target_id,
            )
            if existing is not None and existing.status == "delivered":
                # Already delivered — do NOT call the adapter again (§16.2).
                return TargetResult(
                    target_id=target_id,
                    publication_id=existing.id,
                    status="delivered",
                    external_id=existing.external_id,
                    external_url=existing.external_url,
                )

            target = await targets.get(
                workspace_id=workspace_id, target_id=target_id
            )
            if target is None:
                # Cross-workspace or deleted target — cannot insert a publication
                # (FK), so report a failure result without a row.
                return TargetResult(
                    target_id=target_id,
                    publication_id=None,
                    status="failed",
                    error_message="Target not found",
                )

            await pubs.ensure_pending(
                draft_id=draft_id,
                version_number=version_number,
                target_id=target_id,
                workspace_id=workspace_id,
            )
            pub = await pubs.get(
                draft_id=draft_id,
                version_number=version_number,
                target_id=target_id,
            )
            assert pub is not None
            # Race: another caller delivered between our check and insert —
            # ensure_pending no-op'd against their row, so there is nothing of
            # ours to commit (their transaction already wrote the snapshot).
            if pub.status == "delivered":
                return TargetResult(
                    target_id=target_id,
                    publication_id=pub.id,
                    status="delivered",
                    external_id=pub.external_id,
                    external_url=pub.external_url,
                )
            # Transparency snapshot: written in the SAME transaction as the
            # pending publication insert (committed together below), so a
            # publication row can never exist without its provenance snapshot
            # and the values are frozen BEFORE any downstream re-score. On
            # engine retries the ON CONFLICT no-op preserves the original.
            await snapshot_citations(
                session, publication_id=pub.id, draft_id=draft_id
            )
            await session.commit()
            publication_id = pub.id
            prior_attempts = pub.attempt_count
            channel = target.channel
            config = dict(target.config or {})
            from oryx.core.credential_crypto import decrypt_credentials

            credentials = decrypt_credentials(
                target.credentials, target.credentials_iv
            )

        # --- d. Adapter call OUTSIDE any transaction (network I/O) ---
        adapter = get_channel(channel)
        # Provenance footer (post-freeze patch): every channel EXCEPT webhook gets
        # the citation footer appended to its content string before formatting.
        # Webhook keeps content untouched and receives citations as a separate
        # structured field on publish() instead (it feeds systems, not readers).
        if channel == "webhook":
            publish_content = content
        else:
            publish_content = content + format_citation_footer(
                citations, channel, content=content
            )
        try:
            # format_content first (§ step d) — empty means nothing to publish.
            segments = adapter.format_content(publish_content, None)
            if not segments:
                raise PermanentChannelError("No content to publish")
            if channel == "webhook":
                result = await adapter.publish(
                    publish_content, draft_title, credentials, config,
                    citations=citations,
                )
            else:
                result = await adapter.publish(
                    publish_content, draft_title, credentials, config
                )
        except PermanentChannelError as exc:
            return await self._record_failed(
                draft_id=draft_id,
                target_id=target_id,
                publication_id=publication_id,
                workspace_id=workspace_id,
                channel=channel,
                account_id=account_id,
                error=str(exc),
                attempt_count=None,
                causation_id=causation_id,
                correlation_id=correlation_id,
            )
        except TransientChannelError as exc:
            attempt = prior_attempts + 1
            if attempt >= MAX_PUBLISH_ATTEMPTS:
                return await self._record_failed(
                    draft_id=draft_id,
                    target_id=target_id,
                    publication_id=publication_id,
                    workspace_id=workspace_id,
                    channel=channel,
                    account_id=account_id,
                    error=f"Transient failure, exhausted at {attempt} attempts: {exc}",
                    attempt_count=attempt,
                    causation_id=causation_id,
                    correlation_id=correlation_id,
                )
            # Below the ceiling: leave 'pending' for the drainer/retry mechanism.
            async with self._sm() as session:
                await PublicationsRepository(session).mark_pending_retry(
                    publication_id=publication_id,
                    attempt_count=attempt,
                    error_message=str(exc),
                )
                await session.commit()
            return TargetResult(
                target_id=target_id,
                publication_id=publication_id,
                status="pending",
                error_message=str(exc),
            )

        # --- e. Success: mark delivered + emit CONTENT_PUBLISHED ---
        async with self._sm() as session:
            pubs = PublicationsRepository(session)
            await pubs.mark_delivered(
                publication_id=publication_id,
                external_id=result.external_id,
                external_url=result.external_url,
            )
            await enqueue_event(
                session,
                name=CONTENT_PUBLISHED,
                payload={
                    "draftId": str(draft_id),
                    "publicationId": str(publication_id),
                    "targetId": str(target_id),
                    "channel": channel,
                    "externalId": result.external_id,
                    "workspaceId": str(workspace_id),
                },
                workspace_id=workspace_id,
                actor_kind="account",
                actor_id=str(account_id),
                causation_id=causation_id,
                correlation_id=correlation_id,
            )
            await session.commit()
        return TargetResult(
            target_id=target_id,
            publication_id=publication_id,
            status="delivered",
            external_id=result.external_id,
            external_url=result.external_url,
        )

    async def _record_failed(
        self,
        *,
        draft_id: uuid.UUID,
        target_id: uuid.UUID,
        publication_id: uuid.UUID,
        workspace_id: uuid.UUID,
        channel: str,
        account_id: uuid.UUID,
        error: str,
        attempt_count: int | None,
        causation_id: str | None,
        correlation_id: str | None,
    ) -> TargetResult:
        async with self._sm() as session:
            pubs = PublicationsRepository(session)
            await pubs.mark_failed(
                publication_id=publication_id,
                error_message=error,
                attempt_count=attempt_count,
            )
            await enqueue_event(
                session,
                name=CONTENT_PUBLISH_FAILED,
                payload={
                    "draftId": str(draft_id),
                    "publicationId": str(publication_id),
                    "targetId": str(target_id),
                    "channel": channel,
                    "workspaceId": str(workspace_id),
                    "error": error,
                },
                workspace_id=workspace_id,
                actor_kind="account",
                actor_id=str(account_id),
                causation_id=causation_id,
                correlation_id=correlation_id,
            )
            await session.commit()
        return TargetResult(
            target_id=target_id,
            publication_id=publication_id,
            status="failed",
            error_message=error,
        )

    async def _mark_draft_published_at(
        self, session: AsyncSession, draft_id: uuid.UUID
    ) -> None:
        from datetime import UTC, datetime

        from sqlalchemy import update

        from oryx.core.models import ContentDraft

        await session.execute(
            update(ContentDraft)
            .where(ContentDraft.id == draft_id)
            .values(published_at=datetime.now(UTC))
        )
