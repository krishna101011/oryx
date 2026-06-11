"""Profiles router — /v1/profiles/me GET + PATCH."""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from anant.core.dependencies import (
    db_session,
    envelope,
    get_current_account,
    get_request_id,
)
from anant.core.errors import NotFoundError
from anant.core.models import Account, Profile
from anant.shared.types import Profile as ProfileSchema
from anant.shared.types import UpdateProfileRequest

router = APIRouter(prefix="/profiles", tags=["profiles"])


def _to_schema(p: Profile) -> ProfileSchema:
    return ProfileSchema(
        accountId=str(p.account_id),
        displayName=p.display_name,
        avatarUrl=p.avatar_url,
        headline=p.headline,
        timezone=p.timezone,
        locale=p.locale,
        createdAt=p.created_at,
        updatedAt=p.updated_at,
    )


@router.get("/me")
async def get_me(
    request: Request,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(db_session),
) -> dict:
    result = await db.execute(select(Profile).where(Profile.account_id == account.id))
    profile = result.scalar_one_or_none()
    if profile is None:
        raise NotFoundError("Profile not found")
    return envelope(
        _to_schema(profile).model_dump(by_alias=True),
        request_id=get_request_id(request),
    )


@router.patch("/me")
async def update_me(
    body: UpdateProfileRequest,
    request: Request,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(db_session),
) -> dict:
    patch = body.model_dump(exclude_unset=True, by_alias=False)
    if patch:
        patch["updated_at"] = datetime.now(UTC)
        await db.execute(
            update(Profile).where(Profile.account_id == account.id).values(**patch)
        )
    result = await db.execute(select(Profile).where(Profile.account_id == account.id))
    profile = result.scalar_one_or_none()
    if profile is None:
        raise NotFoundError("Profile not found")
    return envelope(
        _to_schema(profile).model_dump(by_alias=True),
        request_id=get_request_id(request),
    )
