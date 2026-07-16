"""/v1/auth/me — single bootstrap envelope.

Composes account + profile + workspace + preferences + activity unread +
flags + onboarding state in one round-trip so the mobile app cold-boots
without N parallel requests.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.config import get_settings
from oryx.core.dependencies import (
    ActiveWorkspaceContext,
    db_session,
    envelope,
    get_active_workspace,
    get_current_account,
    get_request_id,
)
from oryx.core.errors import NotFoundError
from oryx.core.models import (
    Account,
    ActivityInbox,
    Claim,
    ConflictRecord,
    ContentDraft,
    IntelligenceObject,
    OnboardingState,
    Profile,
    ResearchPacket,
    ResearchWorkspace,
    Workspace,
)
from oryx.core.models import (
    Preferences as PreferencesRow,
)
from oryx.services.feature_flags.resolver import resolve_flags
from oryx.shared.types import (
    Account as AccountSchema,
)
from oryx.shared.types import (
    ActiveWorkspace,
    MeResponse,
    OnboardingStep,
)
from oryx.shared.types import OnboardingState as OnboardingStateLiteral
from oryx.shared.types import (
    Preferences as PreferencesSchema,
)
from oryx.shared.types import (
    Profile as ProfileSchema,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
async def get_me(
    request: Request,
    account: Account = Depends(get_current_account),
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict:
    # Profile
    profile_res = await db.execute(
        select(Profile).where(Profile.account_id == account.id)
    )
    profile = profile_res.scalar_one_or_none()
    if profile is None:
        raise NotFoundError("Profile not found")

    # Workspace
    ws_res = await db.execute(select(Workspace).where(Workspace.id == ws.workspace_id))
    workspace = ws_res.scalar_one()

    # Preferences
    prefs_res = await db.execute(
        select(PreferencesRow).where(PreferencesRow.account_id == account.id)
    )
    prefs = prefs_res.scalar_one()

    # Activity unread count
    unread_res = await db.execute(
        select(func.count())
        .select_from(ActivityInbox)
        .where(
            ActivityInbox.account_id == account.id,
            ActivityInbox.read_at.is_(None),
        )
    )
    unread = int(unread_res.scalar_one() or 0)

    # Flags
    flags = await resolve_flags(
        db, account_id=account.id, workspace_id=ws.workspace_id
    )

    # Onboarding
    ob_res = await db.execute(
        select(OnboardingState).where(OnboardingState.account_id == account.id)
    )
    ob = ob_res.scalar_one_or_none()

    onboarding_state: OnboardingStateLiteral
    next_step: OnboardingStep | None
    if ob is None or ob.completed_at is not None or ob.current_step == "complete":
        onboarding_state = "complete"
        next_step = None
    else:
        onboarding_state = "incomplete"
        # Map current_step → next_step (the step the client should render NOW is current_step).
        next_step = ob.current_step  # type: ignore[assignment]

    # Phase 4 Wave E — verification + research counts (current workspace).
    pending_review_count = int(
        (
            await db.execute(
                select(func.count())
                .select_from(Claim)
                .where(
                    Claim.workspace_id == ws.workspace_id,
                    Claim.requires_analyst_review.is_(True),
                    Claim.superseded_by.is_(None),
                )
            )
        ).scalar_one()
        or 0
    )
    open_conflict_count = int(
        (
            await db.execute(
                select(func.count())
                .select_from(ConflictRecord)
                .where(
                    ConflictRecord.workspace_id == ws.workspace_id,
                    ConflictRecord.status == "open",
                )
            )
        ).scalar_one()
        or 0
    )
    # Command Center VERIFIED stat. Note: claims carry NO verification status —
    # the per-item verdict lives on intelligence_objects.verification_status.
    # 'analyst_approved' counts too: an analyst approval REPLACES 'verified'
    # (review flips the status), so excluding it would make approving an
    # object silently decrement the stat.
    verified_count = int(
        (
            await db.execute(
                select(func.count())
                .select_from(IntelligenceObject)
                .where(
                    IntelligenceObject.workspace_id == ws.workspace_id,
                    IntelligenceObject.verification_status.in_(
                        ("verified", "analyst_approved")
                    ),
                )
            )
        ).scalar_one()
        or 0
    )
    active_workspace_count = int(
        (
            await db.execute(
                select(func.count())
                .select_from(ResearchWorkspace)
                .where(
                    ResearchWorkspace.workspace_id == ws.workspace_id,
                    ResearchWorkspace.account_id == account.id,
                    ResearchWorkspace.status == "active",
                )
            )
        ).scalar_one()
        or 0
    )
    ready_packet_count = int(
        (
            await db.execute(
                select(func.count())
                .select_from(ResearchPacket)
                .where(
                    ResearchPacket.workspace_id == ws.workspace_id,
                    ResearchPacket.status == "ready",
                    ResearchPacket.consumed_at.is_(None),
                )
            )
        ).scalar_one()
        or 0
    )

    # Phase 5 Wave A — content workload counts (current workspace).
    week_ago = datetime.now(UTC) - timedelta(days=7)
    draft_count = int(
        (
            await db.execute(
                select(func.count())
                .select_from(ContentDraft)
                .where(ContentDraft.workspace_id == ws.workspace_id)
            )
        ).scalar_one()
        or 0
    )
    content_pending_review_count = int(
        (
            await db.execute(
                select(func.count())
                .select_from(ContentDraft)
                .where(
                    ContentDraft.workspace_id == ws.workspace_id,
                    ContentDraft.status == "in_review",
                )
            )
        ).scalar_one()
        or 0
    )
    scheduled_count = int(
        (
            await db.execute(
                select(func.count())
                .select_from(ContentDraft)
                .where(
                    ContentDraft.workspace_id == ws.workspace_id,
                    ContentDraft.status == "scheduled",
                )
            )
        ).scalar_one()
        or 0
    )
    published_this_week = int(
        (
            await db.execute(
                select(func.count())
                .select_from(ContentDraft)
                .where(
                    ContentDraft.workspace_id == ws.workspace_id,
                    ContentDraft.status == "published",
                    ContentDraft.published_at >= week_ago,
                )
            )
        ).scalar_one()
        or 0
    )

    settings = get_settings()
    payload = MeResponse(
        account=AccountSchema(
            id=str(account.id),
            email=account.email,
            status=account.status,
            emailVerified=account.email_verified_at is not None,
            isPlatformAdmin=account.is_platform_admin,
            createdAt=account.created_at,
        ),
        profile=ProfileSchema(
            accountId=str(profile.account_id),
            displayName=profile.display_name,
            avatarUrl=profile.avatar_url,
            headline=profile.headline,
            timezone=profile.timezone,
            locale=profile.locale,
            createdAt=profile.created_at,
            updatedAt=profile.updated_at,
        ),
        workspace=ActiveWorkspace(
            id=str(workspace.id),
            name=workspace.name,
            kind=workspace.kind,
            role=ws.role,
        ),
        preferences=PreferencesSchema(
            accountId=str(prefs.account_id),
            focus=prefs.focus,
            contentStyle=prefs.content_style,
            verificationStrictness=prefs.verification_strictness,
            notificationFrequency=prefs.notification_frequency,
            themeMode=prefs.theme_mode,
            customTopics=list(prefs.custom_topics or []),
            createdAt=prefs.created_at,
            updatedAt=prefs.updated_at,
        ),
        activity={"unreadCount": unread},
        flags=flags,
        onboarding={"state": onboarding_state, "nextStep": next_step},
        verification={
            "pendingReviewCount": pending_review_count,
            "openConflictCount": open_conflict_count,
            "verifiedCount": verified_count,
        },
        research={
            "activeWorkspaceCount": active_workspace_count,
            "readyPacketCount": ready_packet_count,
        },
        content={
            "draftCount": draft_count,
            "pendingReviewCount": content_pending_review_count,
            "scheduledCount": scheduled_count,
            "publishedThisWeek": published_this_week,
        },
        serverTime=datetime.now(UTC),
        build={"version": settings.build_version, "commit": settings.build_commit},
    )
    return envelope(payload.model_dump(by_alias=True), request_id=get_request_id(request))
