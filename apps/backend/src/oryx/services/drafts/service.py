"""Drafts orchestration — packet consumption + AI generation + version control.

Wave A contract (the five invariants):

  1. Generation runs on Claude SONNET (DraftGeneratorAI.model).
  2. PacketConsumerHandler sets research_packets.consumed_at and NOTHING else —
     no auto-generation. Generation is a manual analyst action.
  3. One draft per packet. generate_draft is idempotent: if a draft already
     exists for the packet, it is returned unchanged (the UNIQUE(workspace,
     packet) constraint backs this against races).
  4. Append-only versions. Generation, regeneration, and analyst saves each
     INSERT a new draft_versions row; nothing is ever overwritten.
  5. The source-only constraint lives in the generation system context
     (generator.SOURCE_ONLY_MARKER).

Transactional shape mirrors the claims pipeline: the budget check and the
AI call happen outside the write transaction; spend is recorded durably before
the draft is persisted; the draft + version 1 + citations + DRAFT_CREATED commit
together (atomic).
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from oryx.core.errors import (
    BadRequestError,
    NotFoundError,
    PreconditionFailedError,
    RateLimitedError,
)
from oryx.core.logging import get_logger
from oryx.core.models import (
    ContentDraft,
    DraftReview,
    DraftVersion,
    IntelligenceObject,
)
from oryx.services.drafts.events.constants import (
    DRAFT_APPROVED,
    DRAFT_CREATED,
    DRAFT_REJECTED,
    DRAFT_UPDATED,
)
from oryx.services.drafts.generator import DraftGeneratorAI
from oryx.services.drafts.models import ObjectSnapshot
from oryx.services.drafts.repository import DraftsRepository
from oryx.services.queue.bus import DomainEvent
from oryx.services.queue.drainer import PermanentDeliveryError
from oryx.services.queue.outbox import enqueue_event
from oryx.services.templates.service import TemplateService

logger = get_logger(__name__)


def _snapshot(obj: IntelligenceObject) -> ObjectSnapshot:
    return ObjectSnapshot(
        id=obj.id,
        headline=obj.headline,
        epistemic_type=obj.epistemic_type,
        confidence_score=obj.confidence_score,
        key_facts=dict(obj.key_facts or {}),
    )


def _word_count(text: str) -> int:
    return len(text.split())


def _require_note(note: str | None) -> str:
    """Wave C Refinement 1: 'rejected' and 'changes_requested' must carry a
    reason. Service-layer 400 on empty/whitespace, before any DB work — the
    same contract analyst_reviews uses. Returns the trimmed note."""
    trimmed = (note or "").strip()
    if not trimmed:
        raise BadRequestError("A note is required for this review outcome")
    return trimmed


def _self_approval_allowed(
    *, is_platform_admin: bool, strictness: str, is_self: bool
) -> bool:
    """Review policy (§15.3). A reviewer approving someone else's draft is
    always fine. Approving your OWN draft is the rubber-stamp risk: allowed only
    when the reviewing account is a platform admin, or its
    verification_strictness is 'loose'. 'balanced'/'strict' (and the absent
    default, which the caller maps to 'balanced') block it."""
    if not is_self:
        return True
    if is_platform_admin:
        return True
    return strictness == "loose"


class DraftService:
    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        *,
        generator: DraftGeneratorAI | None = None,
        template_service: TemplateService | None = None,
    ) -> None:
        self._sm = sessionmaker
        self._generator = generator or DraftGeneratorAI()
        self._template_svc = template_service or TemplateService(sessionmaker)

    # ---------------- packet consumption (handler path) ----------------

    async def consume_packet(
        self,
        *,
        workspace_id: uuid.UUID,
        packet_id: uuid.UUID,
        causation_event_id: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Invariant #2: set consumed_at, nothing else. No generation here."""
        async with self._sm() as session:
            repo = DraftsRepository(session)
            if not await repo.workspace_exists(workspace_id):
                raise PermanentDeliveryError(
                    f"workspace {workspace_id} deleted — dead-lettering"
                )
            packet = await repo.get_packet(
                workspace_id=workspace_id, packet_id=packet_id
            )
            if packet is None:
                return  # cascade-deleted; nothing to consume
            if packet.consumed_at is not None:
                return  # idempotent: re-delivery is a no-op
            await repo.mark_packet_consumed(packet_id)
            await session.commit()

    # ---------------- generation (analyst path) ----------------

    async def generate_draft(
        self,
        *,
        packet_id: uuid.UUID,
        format: str,
        instructions: str | None,
        account_id: uuid.UUID,
        workspace_id: uuid.UUID,
        template_id: uuid.UUID | None = None,
        correlation_id: str | None = None,
    ) -> ContentDraft:
        # ---- 1. Validate packet + idempotency (invariant #3) ----
        async with self._sm() as session:
            repo = DraftsRepository(session)
            if not await repo.workspace_exists(workspace_id):
                raise NotFoundError("Workspace not found")
            packet = await repo.get_packet(
                workspace_id=workspace_id, packet_id=packet_id
            )
            if packet is None:
                raise NotFoundError("Research packet not found")
            # A draft can only be created from a ready (or already-consumed)
            # packet — verified-only content (blueprint §1).
            if packet.status not in ("ready", "consumed"):
                raise PreconditionFailedError(
                    "Packet is not ready for content generation",
                    details={"status": packet.status},
                )
            existing = await repo.get_draft_by_packet(
                workspace_id=workspace_id, packet_id=packet_id
            )
            if existing is not None:
                return existing  # one draft per packet — return it unchanged
            object_ids = list(packet.intelligence_object_ids or [])
            packet_name = packet.name
            # Intentionally nested in this transaction: if seeding fails the
            # packet is not marked consumed, keeping the boundary atomic.
            resolved_template = await self._template_svc.resolve_template(
                workspace_id, format, template_id, session
            )
            # Mark consumed (idempotent) — handoff marker. If the handler already
            # ran on PACKET_READY this is a no-op.
            await repo.mark_packet_consumed(packet_id)
            await session.commit()

        resolved_template_id = resolved_template.id

        # ---- 2. Load source objects + budget gate ----
        async with self._sm() as session:
            repo = DraftsRepository(session)
            objects = await repo.get_objects(
                workspace_id=workspace_id, ids=object_ids
            )
            if await repo.budget_remaining(workspace_id) <= 0:
                logger.warning(
                    "content.budget_exceeded",
                    extra={
                        "workspace_id": str(workspace_id),
                        "stage": "draft_generator",
                    },
                )
                raise RateLimitedError(
                    "Daily AI budget reached — try again after reset"
                )
        snapshots = [_snapshot(o) for o in objects]
        title = packet_name

        # ---- 3. Generate (Sonnet) — outside any transaction ----
        generated = await self._generator.generate(
            objects=snapshots,
            format=format,
            instructions=instructions,
            template=resolved_template,
        )

        # ---- 4. Record spend durably (tokens were really consumed) ----
        if generated.token_count:
            async with self._sm() as session:
                await DraftsRepository(session).add_tokens_used(
                    workspace_id, generated.token_count
                )
                await session.commit()

        # ---- 5. Persist draft + version 1 + citations + event (atomic) ----
        async with self._sm() as session:
            repo = DraftsRepository(session)
            draft = await repo.create_draft(
                workspace_id=workspace_id,
                account_id=account_id,
                packet_id=packet_id,
                format=format,
                title=title,
                generation_model=self._generator.model,
                generation_version=self._generator.version,
                word_count=generated.word_count,
                template_id=resolved_template_id,
            )
            if draft is None:
                # Lost the one-per-packet race — return the winner's draft.
                winner = await repo.get_draft_by_packet(
                    workspace_id=workspace_id, packet_id=packet_id
                )
                assert winner is not None
                return winner
            await repo.insert_version(
                draft_id=draft.id,
                version_number=1,
                content=generated.content,
                edited_by=account_id,
                is_ai_generated=True,
                word_count=generated.word_count,
                token_count=generated.token_count,
            )
            await repo.insert_citations(
                draft_id=draft.id, object_ids=[o.id for o in objects]
            )
            await enqueue_event(
                session,
                name=DRAFT_CREATED,
                payload={
                    "draftId": str(draft.id),
                    "packetId": str(packet_id),
                    "workspaceId": str(workspace_id),
                    "format": format,
                    "generationModel": self._generator.model,
                    "versionNumber": 1,
                },
                workspace_id=workspace_id,
                actor_kind="account",
                actor_id=str(account_id),
                correlation_id=correlation_id,
            )
            await session.commit()
            refreshed = await repo.get_draft(
                workspace_id=workspace_id, draft_id=draft.id
            )
            assert refreshed is not None
            return refreshed

    async def regenerate_draft(
        self,
        *,
        draft_id: uuid.UUID,
        instructions: str | None,
        account_id: uuid.UUID,
        workspace_id: uuid.UUID,
        correlation_id: str | None = None,
    ) -> ContentDraft:
        # ---- Load draft + its packet's objects (same snapshot) ----
        async with self._sm() as session:
            repo = DraftsRepository(session)
            draft = await repo.get_draft(
                workspace_id=workspace_id, draft_id=draft_id
            )
            if draft is None:
                raise NotFoundError("Draft not found")
            packet = await repo.get_packet(
                workspace_id=workspace_id, packet_id=draft.packet_id
            )
            object_ids = list(packet.intelligence_object_ids or []) if packet else []
            objects = await repo.get_objects(
                workspace_id=workspace_id, ids=object_ids
            )
            fmt = draft.format
            if await repo.budget_remaining(workspace_id) <= 0:
                logger.warning(
                    "content.budget_exceeded",
                    extra={
                        "workspace_id": str(workspace_id),
                        "stage": "draft_regenerator",
                    },
                )
                raise RateLimitedError(
                    "Daily AI budget reached — try again after reset"
                )
        snapshots = [_snapshot(o) for o in objects]

        # ---- Generate (does NOT re-consume packet, does NOT create a draft) ----
        generated = await self._generator.generate(
            objects=snapshots, format=fmt, instructions=instructions
        )
        if generated.token_count:
            async with self._sm() as session:
                await DraftsRepository(session).add_tokens_used(
                    workspace_id, generated.token_count
                )
                await session.commit()

        # ---- Append a new AI version (invariant #4) ----
        return await self._append_version(
            draft_id=draft_id,
            workspace_id=workspace_id,
            content=generated.content,
            edited_by=account_id,
            is_ai_generated=True,
            word_count=generated.word_count,
            token_count=generated.token_count,
            correlation_id=correlation_id,
        )

    # ---------------- analyst edit (save version) ----------------

    async def save_version(
        self,
        *,
        draft_id: uuid.UUID,
        content: str,
        content_html: str | None,
        edit_note: str | None,
        account_id: uuid.UUID,
        workspace_id: uuid.UUID,
        correlation_id: str | None = None,
    ) -> ContentDraft:
        if not content or not content.strip():
            raise BadRequestError("Draft content cannot be empty")
        return await self._append_version(
            draft_id=draft_id,
            workspace_id=workspace_id,
            content=content,
            edited_by=account_id,
            is_ai_generated=False,
            content_html=content_html,
            edit_note=edit_note,
            word_count=_word_count(content),
            token_count=None,
            correlation_id=correlation_id,
            # Wave C Refinement 2: an analyst edit on a draft that was sent back
            # for changes pulls it out of 'changes_requested' and back to 'draft'
            # (the single re-entry point for submit-review). AI regeneration does
            # NOT trigger this — only an explicit analyst save.
            revert_changes_requested=True,
        )

    async def _append_version(
        self,
        *,
        draft_id: uuid.UUID,
        workspace_id: uuid.UUID,
        content: str,
        edited_by: uuid.UUID,
        is_ai_generated: bool,
        word_count: int,
        token_count: int | None,
        content_html: str | None = None,
        edit_note: str | None = None,
        correlation_id: str | None = None,
        revert_changes_requested: bool = False,
    ) -> ContentDraft:
        async with self._sm() as session:
            repo = DraftsRepository(session)
            draft = await repo.get_draft(
                workspace_id=workspace_id, draft_id=draft_id
            )
            if draft is None:
                raise NotFoundError("Draft not found")
            # Status read BEFORE the write — used for the changes_requested
            # auto-revert (Wave C Refinement 2).
            prior_status = draft.status
            next_number = await repo.max_version_number(draft_id) + 1
            await repo.insert_version(
                draft_id=draft_id,
                version_number=next_number,
                content=content,
                edited_by=edited_by,
                is_ai_generated=is_ai_generated,
                content_html=content_html,
                edit_note=edit_note,
                word_count=word_count,
                token_count=token_count,
            )
            await repo.set_current_version(
                draft_id=draft_id,
                version_number=next_number,
                word_count=word_count,
            )
            if revert_changes_requested and prior_status == "changes_requested":
                await repo.set_draft_status(draft_id=draft_id, status="draft")
            await enqueue_event(
                session,
                name=DRAFT_UPDATED,
                payload={
                    "draftId": str(draft_id),
                    "workspaceId": str(workspace_id),
                    "versionNumber": next_number,
                    "editedBy": str(edited_by),
                    "isAiGenerated": is_ai_generated,
                },
                workspace_id=workspace_id,
                actor_kind="account",
                actor_id=str(edited_by),
                correlation_id=correlation_id,
            )
            await session.commit()
            refreshed = await repo.get_draft(
                workspace_id=workspace_id, draft_id=draft_id
            )
            assert refreshed is not None
            return refreshed

    # ---------------- format switching (Wave B) ----------------

    async def switch_format(
        self,
        *,
        draft_id: uuid.UUID,
        new_format: str,
        template_id: uuid.UUID | None,
        workspace_id: uuid.UUID,
        account_id: uuid.UUID,
        correlation_id: str | None = None,
    ) -> ContentDraft:
        """Switch a draft to a new format and regenerate its content.

        Same status guard as regenerate (draft/changes_requested only).
        Resolves a template for the new format, updates the draft row,
        and appends a new AI-generated version — all in a single transaction.
        """
        # ---- Load draft + packet objects (same snapshot path as regenerate) ----
        async with self._sm() as session:
            repo = DraftsRepository(session)
            draft = await repo.get_draft(
                workspace_id=workspace_id, draft_id=draft_id
            )
            if draft is None:
                raise NotFoundError("Draft not found")
            if draft.status not in ("draft", "changes_requested"):
                raise PreconditionFailedError(
                    "Format can only be switched on drafts in 'draft' or "
                    "'changes_requested' status",
                    details={"status": draft.status},
                )
            # Captured before the AI call / write for the changes_requested
            # auto-revert (Wave C Refinement 2).
            prior_status = draft.status
            packet = await repo.get_packet(
                workspace_id=workspace_id, packet_id=draft.packet_id
            )
            object_ids = list(packet.intelligence_object_ids or []) if packet else []
            objects = await repo.get_objects(
                workspace_id=workspace_id, ids=object_ids
            )
            # Resolve template for the NEW format (lazy-seeds defaults if needed).
            resolved_template = await self._template_svc.resolve_template(
                workspace_id, new_format, template_id, session
            )
            if await repo.budget_remaining(workspace_id) <= 0:
                logger.warning(
                    "content.budget_exceeded",
                    extra={
                        "workspace_id": str(workspace_id),
                        "stage": "draft_switch_format",
                    },
                )
                raise RateLimitedError(
                    "Daily AI budget reached — try again after reset"
                )

        snapshots = [_snapshot(o) for o in objects]

        # ---- Generate with the new format + template (outside transaction) ----
        generated = await self._generator.generate(
            objects=snapshots,
            format=new_format,
            instructions=None,
            template=resolved_template,
        )
        if generated.token_count:
            async with self._sm() as session:
                await DraftsRepository(session).add_tokens_used(
                    workspace_id, generated.token_count
                )
                await session.commit()

        # ---- Atomic: update format+template_id + append new version + event ----
        async with self._sm() as session:
            repo = DraftsRepository(session)
            await repo.update_draft_format(
                draft_id=draft_id,
                format=new_format,
                template_id=resolved_template.id,
            )
            next_number = await repo.max_version_number(draft_id) + 1
            await repo.insert_version(
                draft_id=draft_id,
                version_number=next_number,
                content=generated.content,
                edited_by=account_id,
                is_ai_generated=True,
                word_count=generated.word_count,
                token_count=generated.token_count,
            )
            await repo.set_current_version(
                draft_id=draft_id,
                version_number=next_number,
                word_count=generated.word_count,
            )
            if prior_status == "changes_requested":
                await repo.set_draft_status(draft_id=draft_id, status="draft")
            await enqueue_event(
                session,
                name=DRAFT_UPDATED,
                payload={
                    "draftId": str(draft_id),
                    "workspaceId": str(workspace_id),
                    "versionNumber": next_number,
                    "editedBy": str(account_id),
                    "isAiGenerated": True,
                    "formatChanged": new_format,
                },
                workspace_id=workspace_id,
                actor_kind="account",
                actor_id=str(account_id),
                correlation_id=correlation_id,
            )
            await session.commit()
            refreshed = await repo.get_draft(
                workspace_id=workspace_id, draft_id=draft_id
            )
            assert refreshed is not None
            return refreshed

    # ---------------- review workflow (Wave C) ----------------

    async def submit_review(
        self,
        *,
        draft_id: uuid.UUID,
        account_id: uuid.UUID,
        workspace_id: uuid.UUID,
        correlation_id: str | None = None,
    ) -> ContentDraft:
        """draft → in_review. Callable ONLY from 'draft' (Refinement 2): a draft
        sent back for changes re-enters this flow by being edited back to
        'draft' first, never by submitting directly from 'changes_requested'."""
        async with self._sm() as session:
            repo = DraftsRepository(session)
            draft = await repo.get_draft(
                workspace_id=workspace_id, draft_id=draft_id
            )
            if draft is None:
                raise NotFoundError("Draft not found")
            if draft.status != "draft":
                raise PreconditionFailedError(
                    "Only a draft in 'draft' status can be submitted for review",
                    details={"status": draft.status},
                )
            await repo.set_draft_status(draft_id=draft_id, status="in_review")
            await enqueue_event(
                session,
                name=DRAFT_UPDATED,
                payload={
                    "draftId": str(draft_id),
                    "workspaceId": str(workspace_id),
                    "versionNumber": draft.current_version,
                    "submittedBy": str(account_id),
                    "statusChange": "in_review",
                },
                workspace_id=workspace_id,
                actor_kind="account",
                actor_id=str(account_id),
                correlation_id=correlation_id,
            )
            await session.commit()
            refreshed = await repo.get_draft(
                workspace_id=workspace_id, draft_id=draft_id
            )
            assert refreshed is not None
            return refreshed

    async def approve_draft(
        self,
        *,
        draft_id: uuid.UUID,
        account_id: uuid.UUID,
        workspace_id: uuid.UUID,
        note: str | None,
        correlation_id: str | None = None,
    ) -> ContentDraft:
        """in_review → approved. Self-approval is gated by §15.3 review policy;
        a clean approval needs no note (Refinement 1)."""
        async with self._sm() as session:
            repo = DraftsRepository(session)
            draft = await repo.get_draft(
                workspace_id=workspace_id, draft_id=draft_id
            )
            if draft is None:
                raise NotFoundError("Draft not found")
            if draft.status != "in_review":
                raise PreconditionFailedError(
                    "Only a draft in 'in_review' status can be approved",
                    details={"status": draft.status},
                )
            # Self-approval eligibility — keyed on the REVIEWING account's own
            # preference (account-scoped per Phase 2). Absent prefs → 'balanced'.
            is_self = account_id == draft.account_id
            account = await repo.get_account(account_id)
            is_platform_admin = bool(account and account.is_platform_admin)
            strictness = (
                await repo.get_verification_strictness(account_id) or "balanced"
            )
            if not _self_approval_allowed(
                is_platform_admin=is_platform_admin,
                strictness=strictness,
                is_self=is_self,
            ):
                raise PreconditionFailedError(
                    "A different reviewer must approve this draft",
                    details={"policy": strictness},
                )
            clean_note = (note or "").strip() or None
            await repo.insert_review(
                draft_id=draft_id,
                version_number=draft.current_version,
                account_id=account_id,
                outcome="approved",
                note=clean_note,
            )
            await repo.set_draft_status(draft_id=draft_id, status="approved")
            # Causation chain (§8.2): approved ← most recent updated, else created.
            causation_id = await repo.latest_event_id_for_draft(
                draft_id, (DRAFT_UPDATED, DRAFT_CREATED)
            )
            await enqueue_event(
                session,
                name=DRAFT_APPROVED,
                payload={
                    "draftId": str(draft_id),
                    "workspaceId": str(workspace_id),
                    "reviewedBy": str(account_id),
                    "versionNumber": draft.current_version,
                },
                workspace_id=workspace_id,
                actor_kind="account",
                actor_id=str(account_id),
                causation_id=causation_id,
                correlation_id=correlation_id,
            )
            await session.commit()
            refreshed = await repo.get_draft(
                workspace_id=workspace_id, draft_id=draft_id
            )
            assert refreshed is not None
            return refreshed

    async def reject_draft(
        self,
        *,
        draft_id: uuid.UUID,
        account_id: uuid.UUID,
        workspace_id: uuid.UUID,
        note: str,
        correlation_id: str | None = None,
    ) -> ContentDraft:
        """in_review → rejected. Note required (Refinement 1). No self-account
        restriction — rejecting your own work carries no rubber-stamp risk."""
        clean_note = _require_note(note)
        async with self._sm() as session:
            repo = DraftsRepository(session)
            draft = await repo.get_draft(
                workspace_id=workspace_id, draft_id=draft_id
            )
            if draft is None:
                raise NotFoundError("Draft not found")
            if draft.status != "in_review":
                raise PreconditionFailedError(
                    "Only a draft in 'in_review' status can be rejected",
                    details={"status": draft.status},
                )
            await repo.insert_review(
                draft_id=draft_id,
                version_number=draft.current_version,
                account_id=account_id,
                outcome="rejected",
                note=clean_note,
            )
            await repo.set_draft_status(draft_id=draft_id, status="rejected")
            await enqueue_event(
                session,
                name=DRAFT_REJECTED,
                payload={
                    "draftId": str(draft_id),
                    "workspaceId": str(workspace_id),
                    "reviewedBy": str(account_id),
                    "reason": clean_note,
                },
                workspace_id=workspace_id,
                actor_kind="account",
                actor_id=str(account_id),
                correlation_id=correlation_id,
            )
            await session.commit()
            refreshed = await repo.get_draft(
                workspace_id=workspace_id, draft_id=draft_id
            )
            assert refreshed is not None
            return refreshed

    async def request_changes(
        self,
        *,
        draft_id: uuid.UUID,
        account_id: uuid.UUID,
        workspace_id: uuid.UUID,
        note: str,
        correlation_id: str | None = None,
    ) -> ContentDraft:
        """in_review → changes_requested. Note required (Refinement 1). Reuses
        DRAFT_UPDATED — this is an internal lifecycle status, not a distinct
        event. No self-account restriction."""
        clean_note = _require_note(note)
        async with self._sm() as session:
            repo = DraftsRepository(session)
            draft = await repo.get_draft(
                workspace_id=workspace_id, draft_id=draft_id
            )
            if draft is None:
                raise NotFoundError("Draft not found")
            if draft.status != "in_review":
                raise PreconditionFailedError(
                    "Only a draft in 'in_review' status can have changes "
                    "requested",
                    details={"status": draft.status},
                )
            await repo.insert_review(
                draft_id=draft_id,
                version_number=draft.current_version,
                account_id=account_id,
                outcome="changes_requested",
                note=clean_note,
            )
            await repo.set_draft_status(
                draft_id=draft_id, status="changes_requested"
            )
            await enqueue_event(
                session,
                name=DRAFT_UPDATED,
                payload={
                    "draftId": str(draft_id),
                    "workspaceId": str(workspace_id),
                    "versionNumber": draft.current_version,
                    "reviewedBy": str(account_id),
                    "statusChange": "changes_requested",
                },
                workspace_id=workspace_id,
                actor_kind="account",
                actor_id=str(account_id),
                correlation_id=correlation_id,
            )
            await session.commit()
            refreshed = await repo.get_draft(
                workspace_id=workspace_id, draft_id=draft_id
            )
            assert refreshed is not None
            return refreshed

    async def list_reviews(
        self, *, workspace_id: uuid.UUID, draft_id: uuid.UUID
    ) -> list[DraftReview]:
        async with self._sm() as session:
            repo = DraftsRepository(session)
            draft = await repo.get_draft(
                workspace_id=workspace_id, draft_id=draft_id
            )
            if draft is None:
                raise NotFoundError("Draft not found")
            return await repo.list_reviews(draft_id)

    # ---------------- reads ----------------

    async def list_drafts(
        self,
        *,
        workspace_id: uuid.UUID,
        status: str | None = None,
        packet_id: uuid.UUID | None = None,
    ) -> list[ContentDraft]:
        async with self._sm() as session:
            return await DraftsRepository(session).list_drafts(
                workspace_id=workspace_id, status=status, packet_id=packet_id
            )

    async def get_draft_detail(
        self, *, workspace_id: uuid.UUID, draft_id: uuid.UUID
    ) -> tuple[ContentDraft, DraftVersion | None, list[uuid.UUID]]:
        async with self._sm() as session:
            repo = DraftsRepository(session)
            draft = await repo.get_draft(
                workspace_id=workspace_id, draft_id=draft_id
            )
            if draft is None:
                raise NotFoundError("Draft not found")
            current = await repo.get_version(
                draft_id=draft_id, version_number=draft.current_version
            )
            citations = await repo.list_citation_object_ids(draft_id)
            return draft, current, citations

    async def list_versions(
        self, *, workspace_id: uuid.UUID, draft_id: uuid.UUID
    ) -> list[DraftVersion]:
        async with self._sm() as session:
            repo = DraftsRepository(session)
            draft = await repo.get_draft(
                workspace_id=workspace_id, draft_id=draft_id
            )
            if draft is None:
                raise NotFoundError("Draft not found")
            return await repo.list_versions(draft_id)


class PacketConsumerHandler:
    """Subscriber for research.packet.ready (registered in build_bus()).

    Invariant #2: sets research_packets.consumed_at and NOTHING else. It does
    NOT auto-generate a draft — generation is a manual analyst action via
    POST /v1/drafts/generate. Idempotent: re-delivery is a no-op once consumed.
    """

    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        *,
        service: DraftService | None = None,
    ) -> None:
        self._sm = sessionmaker
        self._service = service or DraftService(sessionmaker)

    async def __call__(self, event: DomainEvent) -> None:
        workspace_id = uuid.UUID(event.payload["workspaceId"])
        packet_id = uuid.UUID(event.payload["packetId"])
        await self._service.consume_packet(
            workspace_id=workspace_id,
            packet_id=packet_id,
            causation_event_id=event.id,
            correlation_id=event.correlation_id,
        )
