"""Automation router — Phase 6 Wave B (the transparency view).

GET /v1/automation-log (docs/PHASE_6_ARCHITECTURE.md §5, NEW): a
reverse-chronological merge of the two automation record tables —
automation_log (one row per dispatcher decision, INCLUDING suppressions, so
"why didn't I get this" is answerable) and digest_runs (one row per sent
digest window). Account-scoped; read-only. The /automation/ping stub route is
kept — test_health.py exercises every service's ping.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.core.dependencies import (
    db_session,
    envelope,
    get_current_account,
    get_request_id,
)
from oryx.core.models import Account, AutomationLog, DigestRun
from oryx.shared.types import AutomationLogEntry, AutomationLogResponse

router = APIRouter(tags=["automation"])

# The feed page size — matches /activity/inbox's limit.
FEED_LIMIT = 50


@router.get("/automation/ping")
async def ping(request: Request) -> dict:
    return envelope(
        {"service": "automation", "pong": True}, request_id=get_request_id(request)
    )


def _dispatch_entry(row: AutomationLog) -> AutomationLogEntry:
    return AutomationLogEntry(
        id=str(row.id),
        kind="dispatch",
        action=row.action_taken,
        eventType=row.triggered_by_event_type,
        category=None,
        frequency=None,
        windowStart=None,
        windowEnd=None,
        activityInboxId=str(row.activity_inbox_id) if row.activity_inbox_id else None,
        createdAt=row.created_at,
    )


def _digest_entry(row: DigestRun) -> AutomationLogEntry:
    return AutomationLogEntry(
        id=str(row.id),
        kind="digest",
        action="digest_sent",
        eventType=None,
        category=row.activity_type,
        frequency=row.frequency,
        windowStart=row.window_start,
        windowEnd=row.window_end,
        activityInboxId=None,
        createdAt=row.sent_at,
    )


@router.get("/automation-log")
async def get_automation_log(
    request: Request,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(db_session),
) -> dict:
    log_rows = (
        await db.execute(
            select(AutomationLog)
            .where(AutomationLog.account_id == account.id)
            .order_by(AutomationLog.created_at.desc())
            .limit(FEED_LIMIT)
        )
    ).scalars().all()
    digest_rows = (
        await db.execute(
            select(DigestRun)
            .where(DigestRun.account_id == account.id)
            .order_by(DigestRun.sent_at.desc())
            .limit(FEED_LIMIT)
        )
    ).scalars().all()

    entries = [_dispatch_entry(r) for r in log_rows] + [
        _digest_entry(r) for r in digest_rows
    ]
    entries.sort(key=lambda e: e.created_at, reverse=True)
    payload = AutomationLogResponse(entries=entries[:FEED_LIMIT])
    return envelope(payload.model_dump(by_alias=True), request_id=get_request_id(request))
