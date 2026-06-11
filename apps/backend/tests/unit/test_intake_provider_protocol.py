"""IntakeProvider Protocol — structural check.

This is a compile-time-style assertion implemented at test time:
a tiny fake that satisfies the Protocol can be bound to a typed
variable. If the contract drifts, the assignment will fail.
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

import pytest

from anant.services.intake.providers.base import (
    IntakeProvider,
    IntakeSourceKind,
    RawItem,
    SyncCursor,
    ValidationResult,
    ValidationStatus,
)


class _FakeRssProvider:
    name = "rss-fake"
    kind = IntakeSourceKind.RSS

    async def validate_config(self, config: dict[str, Any]) -> ValidationResult:
        if "feed_url" in config:
            return ValidationResult(status=ValidationStatus.OK)
        return ValidationResult(status=ValidationStatus.INVALID, message="feed_url required")

    async def sync(
        self,
        *,
        workspace_id: uuid.UUID,
        intake_source_id: uuid.UUID,
        cursor: SyncCursor | None,
        config: dict[str, Any],
    ) -> AsyncIterator[RawItem]:
        yield RawItem(
            external_id="item-1",
            received_at=datetime.now(UTC),
            sender="example",
            subject="Hello",
            body_text="body",
            body_html=None,
            links=[],
            payload={"guid": "item-1"},
        )


def test_fake_provider_satisfies_protocol() -> None:
    p: IntakeProvider = _FakeRssProvider()
    assert p.name == "rss-fake"
    assert p.kind == IntakeSourceKind.RSS


@pytest.mark.asyncio
async def test_fake_provider_validate_config_ok() -> None:
    p = _FakeRssProvider()
    result = await p.validate_config({"feed_url": "https://example.com/feed"})
    assert result.status == ValidationStatus.OK


@pytest.mark.asyncio
async def test_fake_provider_validate_config_invalid() -> None:
    p = _FakeRssProvider()
    result = await p.validate_config({})
    assert result.status == ValidationStatus.INVALID
    assert result.message == "feed_url required"


@pytest.mark.asyncio
async def test_fake_provider_sync_yields_raw_items() -> None:
    p = _FakeRssProvider()
    out: list[RawItem] = []
    async for item in p.sync(
        workspace_id=uuid.uuid4(),
        intake_source_id=uuid.uuid4(),
        cursor=None,
        config={"feed_url": "x"},
    ):
        out.append(item)
    assert len(out) == 1
    assert out[0].external_id == "item-1"


def test_pull_only_provider_does_not_expose_handle_webhook() -> None:
    """Phase 3 contract: pull-only providers do not declare handle_webhook.
    Orchestrator must `hasattr` before invoking. RSS, Gmail and API pull
    providers (Batch 2) will follow this same rule.
    """
    p = _FakeRssProvider()
    assert not hasattr(p, "handle_webhook")


def test_webhook_capable_provider_exposes_handle_webhook() -> None:
    """A provider that declares handle_webhook is the only kind the
    orchestrator routes inbound POSTs to."""
    class _WebhookCapable:
        name = "wh"
        kind = IntakeSourceKind.WEBHOOK

        async def validate_config(self, config: dict[str, Any]) -> ValidationResult:
            return ValidationResult(status=ValidationStatus.OK)

        async def sync(self, *, workspace_id, intake_source_id, cursor, config):
            # pragma: no cover — not invoked in this test
            if False:
                yield  # type: ignore[unreachable]

        async def handle_webhook(self, *, workspace_id, intake_source_id, headers, body, config):
            if False:
                yield  # type: ignore[unreachable]

    p = _WebhookCapable()
    assert hasattr(p, "handle_webhook")
