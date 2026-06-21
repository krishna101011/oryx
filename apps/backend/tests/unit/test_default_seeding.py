"""Unit tests for ensure_default_templates — idempotency and uniqueness."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from oryx.services.templates.service import TemplateService


def _make_svc():
    sm = MagicMock()
    sm.return_value = AsyncMock()
    return TemplateService(sm)


@pytest.mark.asyncio
async def test_ensure_default_templates_calls_seed():
    """ensure_default_templates delegates to repo.seed_defaults once."""
    svc = _make_svc()
    session = AsyncMock()
    workspace_id = uuid.uuid4()

    with patch("oryx.services.templates.service.TemplatesRepository") as MockRepo:
        instance = MockRepo.return_value
        instance.seed_defaults = AsyncMock()

        await svc.ensure_default_templates(workspace_id, session)

    instance.seed_defaults.assert_awaited_once_with(workspace_id)


@pytest.mark.asyncio
async def test_list_templates_seeds_on_empty_workspace():
    """list_templates calls ensure_default_templates when count == 0."""
    svc = _make_svc()
    session = AsyncMock()
    workspace_id = uuid.uuid4()
    session.flush = AsyncMock()

    with patch("oryx.services.templates.service.TemplatesRepository") as MockRepo:
        instance = MockRepo.return_value
        instance.count_for_workspace = AsyncMock(return_value=0)
        instance.seed_defaults = AsyncMock()
        instance.list_for_workspace = AsyncMock(return_value=[])

        await svc.list_templates(workspace_id, session=session)

    instance.seed_defaults.assert_awaited_once_with(workspace_id)


@pytest.mark.asyncio
async def test_list_templates_skips_seed_when_populated():
    """list_templates does NOT call seed_defaults when templates already exist."""
    svc = _make_svc()
    session = AsyncMock()
    workspace_id = uuid.uuid4()

    with patch("oryx.services.templates.service.TemplatesRepository") as MockRepo:
        instance = MockRepo.return_value
        instance.count_for_workspace = AsyncMock(return_value=6)
        instance.seed_defaults = AsyncMock()
        instance.list_for_workspace = AsyncMock(return_value=[])

        await svc.list_templates(workspace_id, session=session)

    instance.seed_defaults.assert_not_awaited()
