"""/v1/auth/me — single bootstrap envelope.

Composes account + profile + workspace + preferences + activity unread +
flags + onboarding state in one round-trip so the mobile app cold-boots
without N parallel requests.
"""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from anant.config import get_settings
from anant.core.dependencies import (
    ActiveWorkspaceContext,
    db_session,
    envelope,
    get_active_workspace,
    get_current_account,
    get_request_id,
)
from anant.core.errors import NotFoundError
from anant.core.models import (
    Account,
    ActivityInbox,
    OnboardingState,
    Profile,
    Workspace,
)
from anant.core.models import (
    Preferences as PreferencesRow,
)
from anant.services.feature_flags.resolver import resolve_flags
from anant.shared.types import (
    Account as AccountSchema,
)
from anant.shared.types import (
    ActiveWorkspace,
    MeResponse,
    OnboardingStep,
)
from anant.shared.types import OnboardingState as OnboardingStateLiteral
from anant.shared.types import (
    Preferences as PreferencesSchema,
)
from anant.shared.types import (
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
            customTopics=list(prefs.custom_topics or []),
            createdAt=prefs.created_at,
            updatedAt=prefs.updated_at,
        ),
        activity={"unreadCount": unread},
        flags=flags,
        onboarding={"state": onboarding_state, "nextStep": next_step},
        serverTime=datetime.now(UTC),
        build={"version": settings.build_version, "commit": settings.build_commit},
    )
    return envelope(payload.model_dump(by_alias=True), request_id=get_request_id(request))
