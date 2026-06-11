"""Auth audit logging.

Every auth event writes both a structured log AND an auth_audit_log row.
Code paths that mutate authentication state import `record_auth_event`.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from anant.core.logging import get_logger
from anant.core.models import AuthAuditLog

logger = get_logger(__name__)


async def record_auth_event(
    session: AsyncSession,
    *,
    event: str,
    account_id: uuid.UUID | None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    data: dict[str, Any] | None = None,
) -> None:
    row = AuthAuditLog(
        id=uuid.uuid4(),
        account_id=account_id,
        event=event,
        ip_address=ip_address,
        user_agent=user_agent,
        data=data or {},
    )
    session.add(row)
    # Caller commits inside its transaction.
    logger.info(
        "auth.event",
        extra={
            "event": event,
            "account_id": str(account_id) if account_id else None,
        },
    )
