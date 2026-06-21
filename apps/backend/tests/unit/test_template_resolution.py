"""Unit tests for resolve_template — wrong-workspace and format-mismatch rejection.

These run without a database; we inject fake repository behaviour directly.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from oryx.core.errors import BadRequestError, NotFoundError
from oryx.services.templates.service import TemplateService


def _fake_row(*, workspace_id: uuid.UUID, format: str, is_default: bool = False):
    row = MagicMock()
    row.id = uuid.uuid4()
    row.workspace_id = workspace_id
    row.name = f"Default {format}"
    row.format = format
    row.tone = "analytical"
    row.max_words = None
    row.min_words = None
    row.structure_hint = None
    row.is_default = is_default
    return row


def _make_svc():
    sm = MagicMock()
    sm.return_value = AsyncMock()
    return TemplateService(sm)


@pytest.mark.asyncio
async def test_resolve_wrong_workspace_raises_not_found():
    """resolve_template with a template owned by a different workspace → NotFoundError."""
    svc = _make_svc()
    session = AsyncMock()
    template_id = uuid.uuid4()
    owner_ws = uuid.uuid4()
    caller_ws = uuid.uuid4()

    row = _fake_row(workspace_id=owner_ws, format="article")
    row.id = template_id

    with patch("oryx.services.templates.service.TemplatesRepository") as MockRepo:
        instance = MockRepo.return_value
        instance.get_by_id = AsyncMock(return_value=row)

        with pytest.raises(NotFoundError):
            await svc.resolve_template(caller_ws, "article", template_id, session)


@pytest.mark.asyncio
async def test_resolve_format_mismatch_raises_bad_request():
    """resolve_template with template.format != requested format → BadRequestError."""
    svc = _make_svc()
    session = AsyncMock()
    workspace_id = uuid.uuid4()
    template_id = uuid.uuid4()

    row = _fake_row(workspace_id=workspace_id, format="article")
    row.id = template_id

    with patch("oryx.services.templates.service.TemplatesRepository") as MockRepo:
        instance = MockRepo.return_value
        instance.get_by_id = AsyncMock(return_value=row)

        with pytest.raises(BadRequestError):
            await svc.resolve_template(workspace_id, "tweet_thread", template_id, session)


@pytest.mark.asyncio
async def test_resolve_no_template_id_returns_default():
    """resolve_template without template_id returns the default for the format."""
    svc = _make_svc()
    session = AsyncMock()
    workspace_id = uuid.uuid4()

    default_row = _fake_row(workspace_id=workspace_id, format="article", is_default=True)

    with patch("oryx.services.templates.service.TemplatesRepository") as MockRepo:
        instance = MockRepo.return_value
        instance.count_for_workspace = AsyncMock(return_value=1)
        instance.get_default = AsyncMock(return_value=default_row)

        result = await svc.resolve_template(workspace_id, "article", None, session)

    assert result.format == "article"
    assert result.is_default is True


@pytest.mark.asyncio
async def test_resolve_template_not_found_raises_not_found():
    """resolve_template with template_id that doesn't exist → NotFoundError."""
    svc = _make_svc()
    session = AsyncMock()
    workspace_id = uuid.uuid4()
    template_id = uuid.uuid4()

    with patch("oryx.services.templates.service.TemplatesRepository") as MockRepo:
        instance = MockRepo.return_value
        instance.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await svc.resolve_template(workspace_id, "article", template_id, session)
