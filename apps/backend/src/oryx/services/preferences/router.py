"""Preferences router — /v1/preferences GET + PATCH."""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.core.dependencies import (
    db_session,
    envelope,
    get_current_account,
    get_request_id,
)
from oryx.core.errors import NotFoundError
from oryx.core.models import Account
from oryx.core.models import Preferences as PreferencesRow
from oryx.shared.types import Preferences, UpdatePreferencesRequest

router = APIRouter(prefix="/preferences", tags=["preferences"])


def _to_schema(p: PreferencesRow) -> Preferences:
    return Preferences(
        accountId=str(p.account_id),
        focus=p.focus,
        contentStyle=p.content_style,
        verificationStrictness=p.verification_strictness,
        notificationFrequency=p.notification_frequency,
        customTopics=list(p.custom_topics or []),
        createdAt=p.created_at,
        updatedAt=p.updated_at,
    )


@router.get("")
async def get_prefs(
    request: Request,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(db_session),
) -> dict:
    result = await db.execute(
        select(PreferencesRow).where(PreferencesRow.account_id == account.id)
    )
    prefs = result.scalar_one_or_none()
    if prefs is None:
        raise NotFoundError("Preferences not found")
    return envelope(
        _to_schema(prefs).model_dump(by_alias=True), request_id=get_request_id(request)
    )


@router.patch("")
async def patch_prefs(
    body: UpdatePreferencesRequest,
    request: Request,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(db_session),
) -> dict:
    patch = body.model_dump(exclude_unset=True, by_alias=False)
    if patch:
        patch["updated_at"] = datetime.now(UTC)
        await db.execute(
            update(PreferencesRow)
            .where(PreferencesRow.account_id == account.id)
            .values(**patch)
        )
    result = await db.execute(
        select(PreferencesRow).where(PreferencesRow.account_id == account.id)
    )
    prefs = result.scalar_one_or_none()
    if prefs is None:
        raise NotFoundError("Preferences not found")
    return envelope(
        _to_schema(prefs).model_dump(by_alias=True), request_id=get_request_id(request)
    )
