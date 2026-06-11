"""Onboarding — 4-step durable state machine.

Step order:
  welcome -> focus_sources -> notifications_permissions -> style_strictness -> complete

Each POST is idempotent: the server merges the step's choices into preferences/
workspace_sources and advances current_step. A second POST of the same step
is a no-op except for updated_at.
"""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from anant.core.dependencies import (
    ActiveWorkspaceContext,
    db_session,
    envelope,
    get_active_workspace,
    get_current_account,
    get_request_id,
)
from anant.core.errors import ValidationError
from anant.core.models import (
    Account,
    OnboardingState,
    Preferences,
    WorkspaceSource,
)
from anant.shared.types import OnboardingStepRequest, OnboardingStepResponse

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

# Step transitions: current -> next (None means complete).
_NEXT_STEP: dict[str, str | None] = {
    "welcome": "focus_sources",
    "focus_sources": "notifications_permissions",
    "notifications_permissions": "style_strictness",
    "style_strictness": "complete",
    "complete": None,
}


def _to_response(state: OnboardingState) -> OnboardingStepResponse:
    if state.completed_at is not None or state.current_step == "complete":
        return OnboardingStepResponse(state="complete", nextStep=None)
    next_step = _NEXT_STEP.get(state.current_step)
    return OnboardingStepResponse(
        state="incomplete",
        nextStep=next_step if next_step != "complete" else None,
    )


@router.post("/step")
async def post_step(
    body: OnboardingStepRequest,
    request: Request,
    account: Account = Depends(get_current_account),
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict:
    state_res = await db.execute(
        select(OnboardingState).where(OnboardingState.account_id == account.id)
    )
    state = state_res.scalar_one_or_none()
    if state is None:
        raise ValidationError("Onboarding state missing")

    step = body.step
    if step not in _NEXT_STEP:
        raise ValidationError("Unknown onboarding step")

    # Step 2: focus_sources -> persist focus + custom_topics + enabled sources
    if step == "focus_sources":
        prefs_patch: dict = {}
        if body.focus is not None:
            prefs_patch["focus"] = body.focus
        if body.custom_topics is not None:
            prefs_patch["custom_topics"] = body.custom_topics
        if prefs_patch:
            prefs_patch["updated_at"] = datetime.now(UTC)
            await db.execute(
                update(Preferences)
                .where(Preferences.account_id == account.id)
                .values(**prefs_patch)
            )
        if body.enabled_source_keys is not None:
            for key in body.enabled_source_keys:
                stmt = pg_insert(WorkspaceSource).values(
                    workspace_id=ws.workspace_id, source_key=key, enabled=True
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=["workspace_id", "source_key"],
                    set_={"enabled": True},
                )
                await db.execute(stmt)

    # Step 3: notifications_permissions -> notification_frequency
    if step == "notifications_permissions":
        if body.notification_frequency is not None:
            await db.execute(
                update(Preferences)
                .where(Preferences.account_id == account.id)
                .values(
                    notification_frequency=body.notification_frequency,
                    updated_at=datetime.now(UTC),
                )
            )
        # push_permission_granted is captured client-side as a device registration;
        # nothing to persist here in Phase 2 beyond optionally noting the choice.

    # Step 4: style_strictness -> content_style + verification_strictness
    if step == "style_strictness":
        patch: dict = {}
        if body.content_style is not None:
            patch["content_style"] = body.content_style
        if body.verification_strictness is not None:
            patch["verification_strictness"] = body.verification_strictness
        if patch:
            patch["updated_at"] = datetime.now(UTC)
            await db.execute(
                update(Preferences)
                .where(Preferences.account_id == account.id)
                .values(**patch)
            )

    # Advance state
    next_step = _NEXT_STEP[step]
    new_state_values: dict = {"updated_at": datetime.now(UTC)}
    if next_step is None or next_step == "complete":
        new_state_values["current_step"] = "complete"
        new_state_values["completed_at"] = datetime.now(UTC)
    else:
        new_state_values["current_step"] = next_step

    await db.execute(
        update(OnboardingState)
        .where(OnboardingState.account_id == account.id)
        .values(**new_state_values)
    )

    reread = await db.execute(
        select(OnboardingState).where(OnboardingState.account_id == account.id)
    )
    fresh = reread.scalar_one()
    payload = _to_response(fresh)
    return envelope(payload.model_dump(by_alias=True), request_id=get_request_id(request))


@router.post("/skip")
async def skip(
    request: Request,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(db_session),
) -> dict:
    await db.execute(
        update(OnboardingState)
        .where(OnboardingState.account_id == account.id)
        .values(
            current_step="complete",
            completed_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
    )
    payload = OnboardingStepResponse(state="complete", nextStep=None)
    return envelope(payload.model_dump(by_alias=True), request_id=get_request_id(request))
