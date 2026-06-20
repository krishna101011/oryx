"""WebhookProvider — the IntakeProvider implementation for kind=webhook.

Note: pull-only providers (RSS, Gmail, API pull) do not define `handle_webhook`.
This provider is webhook-CAPABLE: the router's `hasattr(provider, "handle_webhook")`
check matches against this class so the router knows to route inbound POSTs
here.

`sync()` is implemented as a no-op stream because:
  - Webhooks are push-only by definition; there's nothing to "pull"
  - The scheduler's contract is "call sync() on every healthy source"; a no-op
    keeps the source healthy without doing useless network work
"""
from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from typing import Any

from oryx.services.intake.providers.base import (
    IntakeSourceKind,
    RawItem,
    SyncCursor,
    ValidationResult,
    ValidationStatus,
)
from oryx.services.intake.providers.webhook.config_schema import (
    WebhookSourceConfig,
)
from oryx.services.intake.providers.webhook.mapper import json_to_raw_item


class WebhookProvider:
    name = "webhook"
    kind = IntakeSourceKind.WEBHOOK

    async def validate_config(self, config: dict[str, Any]) -> ValidationResult:
        try:
            WebhookSourceConfig.model_validate(config)
            return ValidationResult(status=ValidationStatus.OK)
        except Exception as e:
            return ValidationResult(
                status=ValidationStatus.INVALID, message=str(e)
            )

    async def sync(
        self,
        *,
        workspace_id: uuid.UUID,
        intake_source_id: uuid.UUID,
        cursor: SyncCursor | None,
        config: dict[str, Any],
    ) -> AsyncIterator[RawItem]:
        # No-op: webhooks are push-only.
        if False:  # pragma: no cover — keeps the type as AsyncIterator
            yield RawItem(  # type: ignore[unreachable]
                external_id="",
                received_at=__import__("datetime").datetime.now(),
                sender=None, subject=None, body_text=None, body_html=None,
                links=[], payload={},
            )

    async def handle_webhook(
        self,
        *,
        workspace_id: uuid.UUID,
        intake_source_id: uuid.UUID,
        headers: dict[str, str],
        body: bytes,
        config: dict[str, Any],
    ) -> AsyncIterator[RawItem]:
        """Parse the verified body and yield a single RawItem.

        The router has ALREADY:
          - verified the HMAC
          - validated the timestamp window
          - dedupe-checked the idempotency key
          - capped the body size
        This method does the structural transformation only.
        """
        parsed_config = WebhookSourceConfig.model_validate(config)
        body_json: dict[str, Any] = json.loads(body.decode("utf-8") or "{}")
        if not isinstance(body_json, dict):
            # Convert top-level arrays to a wrapped dict for consistency.
            body_json = {"items": body_json}
        yield json_to_raw_item(body_json, mapping=parsed_config.mapping)
