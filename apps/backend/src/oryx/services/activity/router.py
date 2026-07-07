"""Activity router — /v1/activity/*

- inbox: in-app feed (security + system events in Phase 2)
- alerts/preferences: per-type/channel frequency model
- devices: push token registration (delivery is Phase 6)
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.core.dependencies import (
    db_session,
    envelope,
    get_current_account,
    get_request_id,
)
from oryx.core.errors import NotFoundError
from oryx.core.models import (
    Account,
    ActivityInbox,
    AlertDevice,
)
from oryx.core.models import (
    AlertPreference as AlertPreferenceRow,
)
from oryx.services.activity.preferences import (
    DEFAULT_ALERT_FREQUENCY,
    NOTIFICATION_CATEGORIES,
    RESOLVED_CHANNELS,
)
from oryx.shared.types import (
    ActivityInboxResponse,
    ActivityItem,
    RegisterAlertDeviceRequest,
    UpdateAlertPreferenceRequest,
)
from oryx.shared.types import (
    AlertDevice as AlertDeviceSchema,
)
from oryx.shared.types import (
    AlertPreference as AlertPreferenceSchema,
)

router = APIRouter(prefix="/activity", tags=["activity"])


# -------------------- inbox --------------------

def _item_to_schema(row: ActivityInbox) -> ActivityItem:
    return ActivityItem(
        id=str(row.id),
        type=row.type,
        title=row.title,
        body=row.body,
        data=dict(row.data or {}),
        readAt=row.read_at,
        createdAt=row.created_at,
    )


@router.get("/inbox")
async def get_inbox(
    request: Request,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(db_session),
) -> dict:
    items_res = await db.execute(
        select(ActivityInbox)
        .where(ActivityInbox.account_id == account.id)
        .order_by(ActivityInbox.created_at.desc())
        .limit(50)
    )
    items = list(items_res.scalars().all())
    unread_res = await db.execute(
        select(func.count())
        .select_from(ActivityInbox)
        .where(
            ActivityInbox.account_id == account.id,
            ActivityInbox.read_at.is_(None),
        )
    )
    unread = int(unread_res.scalar_one() or 0)
    payload = ActivityInboxResponse(
        items=[_item_to_schema(i) for i in items], unreadCount=unread
    )
    return envelope(payload.model_dump(by_alias=True), request_id=get_request_id(request))


@router.post("/inbox/{item_id}/read")
async def mark_read(
    item_id: uuid.UUID,
    request: Request,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(db_session),
) -> dict:
    result = await db.execute(
        update(ActivityInbox)
        .where(
            ActivityInbox.id == item_id,
            ActivityInbox.account_id == account.id,
            ActivityInbox.read_at.is_(None),
        )
        .values(read_at=datetime.now(UTC))
        .returning(ActivityInbox.id)
    )
    if result.scalar_one_or_none() is None:
        # Either already-read or not found; idempotent success.
        existing = await db.execute(
            select(ActivityInbox).where(
                ActivityInbox.id == item_id, ActivityInbox.account_id == account.id
            )
        )
        if existing.scalar_one_or_none() is None:
            raise NotFoundError("Activity item not found")
    return envelope({"ok": True}, request_id=get_request_id(request))


# -------------------- alerts/preferences --------------------

@router.get("/alerts/preferences")
async def list_alert_prefs(
    request: Request,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(db_session),
) -> dict:
    """The RESOLVED preference grid (Phase 6, docs/PHASE_6_ARCHITECTURE.md §5).

    Every real category x channel combination is returned; a combination with
    no stored row is backfilled with the shared default from
    services/activity/preferences.py — the same resolution the dispatcher
    applies — so the client never reconstructs default logic. Response schema
    is unchanged (a list of AlertPreference); it is now simply complete.
    """
    result = await db.execute(
        select(AlertPreferenceRow).where(AlertPreferenceRow.account_id == account.id)
    )
    existing = {(r.type, r.channel): r for r in result.scalars().all()}
    payload = []
    for category in NOTIFICATION_CATEGORIES:
        for channel in RESOLVED_CHANNELS:
            row = existing.get((category, channel))
            payload.append(
                AlertPreferenceSchema(
                    type=category,
                    channel=channel,
                    frequency=row.frequency if row else DEFAULT_ALERT_FREQUENCY,
                    quietHours=row.quiet_hours if row else None,
                ).model_dump(by_alias=True)
            )
    return envelope(payload, request_id=get_request_id(request))


@router.put("/alerts/preferences/{type}/{channel}")
async def upsert_alert_pref(
    type: str,
    channel: str,
    body: UpdateAlertPreferenceRequest,
    request: Request,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(db_session),
) -> dict:
    values: dict = {
        "account_id": account.id, "type": type, "channel": channel,
        "frequency": body.frequency or "instant",
        "updated_at": datetime.now(UTC),
    }
    if body.quiet_hours is not None:
        values["quiet_hours"] = body.quiet_hours.model_dump() if hasattr(body.quiet_hours, "model_dump") else body.quiet_hours

    stmt = pg_insert(AlertPreferenceRow).values(**values)
    update_cols = {k: stmt.excluded[k] for k in ("frequency", "quiet_hours", "updated_at") if k in values}
    stmt = stmt.on_conflict_do_update(
        index_elements=["account_id", "type", "channel"], set_=update_cols
    )
    await db.execute(stmt)

    result = await db.execute(
        select(AlertPreferenceRow).where(
            AlertPreferenceRow.account_id == account.id,
            AlertPreferenceRow.type == type,
            AlertPreferenceRow.channel == channel,
        )
    )
    row = result.scalar_one()
    payload = AlertPreferenceSchema(
        type=row.type, channel=row.channel, frequency=row.frequency,
        quietHours=row.quiet_hours,
    )
    return envelope(payload.model_dump(by_alias=True), request_id=get_request_id(request))


# -------------------- devices --------------------

@router.post("/devices")
async def register_device(
    body: RegisterAlertDeviceRequest,
    request: Request,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(db_session),
) -> dict:
    device = AlertDevice(
        id=uuid.uuid4(),
        account_id=account.id,
        platform=body.platform,
        push_token=body.push_token,
        app_version=body.app_version,
    )
    db.add(device)
    await db.flush()
    payload = AlertDeviceSchema(
        id=str(device.id),
        platform=device.platform,
        appVersion=device.app_version,
        lastSeenAt=device.last_seen_at,
    )
    return envelope(payload.model_dump(by_alias=True), request_id=get_request_id(request))


@router.delete("/devices/{device_id}")
async def remove_device(
    device_id: uuid.UUID,
    request: Request,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(db_session),
) -> dict:
    await db.execute(
        update(AlertDevice)
        .where(AlertDevice.id == device_id, AlertDevice.account_id == account.id)
        .values(disabled_at=datetime.now(UTC))
    )
    return envelope({"ok": True}, request_id=get_request_id(request))
