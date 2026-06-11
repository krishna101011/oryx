"""Platform-admin gate + monoprocess colocation guard.

DB-free: the full admin endpoints run in the requires_db integration suite.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from anant.core.dependencies import require_platform_admin
from anant.core.errors import PermissionDeniedError
from anant.main import should_colocate


@pytest.mark.asyncio
async def test_platform_admin_passes() -> None:
    account = SimpleNamespace(is_platform_admin=True)
    assert await require_platform_admin(account) is account


@pytest.mark.asyncio
async def test_workspace_owner_without_flag_is_denied() -> None:
    # Owning a workspace grants every workspace capability — but NOT the
    # account-level platform flag (§17.4).
    account = SimpleNamespace(is_platform_admin=False)
    with pytest.raises(PermissionDeniedError):
        await require_platform_admin(account)


def test_colocation_requires_flag_and_dev_environment() -> None:
    s = SimpleNamespace
    assert should_colocate(s(anant_dev_monoprocess=True, environment="dev"))
    assert not should_colocate(s(anant_dev_monoprocess=False, environment="dev"))
    # The hard stop: a stray flag never colocates outside dev.
    assert not should_colocate(s(anant_dev_monoprocess=True, environment="prod"))
    assert not should_colocate(s(anant_dev_monoprocess=True, environment="staging"))
