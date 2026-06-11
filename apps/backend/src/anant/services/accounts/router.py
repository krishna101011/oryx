"""Accounts router — read-only in Phase 2."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request

from anant.core.dependencies import envelope, get_current_account, get_request_id
from anant.core.errors import PermissionDeniedError
from anant.core.models import Account
from anant.shared.types import Account as AccountSchema

router = APIRouter(prefix="/users", tags=["accounts"])


def _to_schema(account: Account) -> AccountSchema:
    return AccountSchema(
        id=str(account.id),
        email=account.email,
        status=account.status,
        emailVerified=account.email_verified_at is not None,
        createdAt=account.created_at,
    )


@router.get("/{account_id}")
async def get_account(
    account_id: uuid.UUID,
    request: Request,
    current: Account = Depends(get_current_account),
) -> dict:
    # Account isolation: only your own.
    if account_id != current.id:
        raise PermissionDeniedError()
    return envelope(
        _to_schema(current).model_dump(by_alias=True),
        request_id=get_request_id(request),
    )
