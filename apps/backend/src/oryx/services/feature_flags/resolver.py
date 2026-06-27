"""Feature flag resolver.

Resolution order:  account override -> workspace override -> global default
A non-expired override wins over an expired one at the same scope.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.config import get_settings
from oryx.core.models import FeatureFlag, FeatureFlagOverride

# Flags whose global default is OFF in the frozen schema but which gate
# already-built screens. In the local **dev** environment they default ON so a
# missing per-workspace override row doesn't silently show "Coming soon" for a
# shipped feature (the recurring screenshot bug). Dev-only — production resolves
# straight from FeatureFlag.default_enabled. Scoped the same way as
# oryx_dev_monoprocess (settings.environment == "dev"). An explicit account/
# workspace override still wins, since overrides are applied afterwards.
_DEV_DEFAULT_ON: frozenset[str] = frozenset({"ff_content_drafts", "ff_research"})


async def resolve_flags(
    db: AsyncSession,
    *,
    account_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> dict[str, bool]:
    flags_res = await db.execute(select(FeatureFlag))
    flags = {f.key: f.default_enabled for f in flags_res.scalars().all()}

    if get_settings().environment == "dev":
        for key in _DEV_DEFAULT_ON:
            flags[key] = True

    now = datetime.now(UTC)
    overrides_res = await db.execute(
        select(FeatureFlagOverride).where(
            (
                (FeatureFlagOverride.scope == "workspace")
                & (FeatureFlagOverride.scope_id == workspace_id)
            )
            | (
                (FeatureFlagOverride.scope == "account")
                & (FeatureFlagOverride.scope_id == account_id)
            )
        )
    )
    overrides = list(overrides_res.scalars().all())

    # Workspace first, then account so account wins on ties.
    for override in sorted(
        overrides, key=lambda o: 0 if o.scope == "workspace" else 1
    ):
        if override.expires_at and override.expires_at < now:
            continue
        flags[override.flag_key] = override.enabled

    return flags


async def resolve_flag(
    db: AsyncSession,
    *,
    key: str,
    account_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> bool:
    flags = await resolve_flags(db, account_id=account_id, workspace_id=workspace_id)
    return flags.get(key, False)
