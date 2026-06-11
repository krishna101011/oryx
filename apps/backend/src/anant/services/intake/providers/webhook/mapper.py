"""generic_json mapper — dotted-path field extraction.

Vendor-specific providers can ship their own mappers in Phase 3.x; this
module is the default for plain JSON webhooks. The template lives in
`WebhookSourceConfig.mapping`.

Path syntax:
    "id"               → top-level
    "event.id"         → nested
    "data.items[0].id" → array indexing
"""
from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from typing import Any

from anant.services.intake.providers.base import RawItem
from anant.services.intake.providers.webhook.config_schema import (
    WebhookFieldMapping,
)

_PATH_RE = re.compile(r"([a-zA-Z_][a-zA-Z0-9_]*)|\[(\d+)\]")


def lookup_path(payload: Any, path: str | None) -> Any:
    if not path:
        return None
    node: Any = payload
    for ident, idx in _PATH_RE.findall(path):
        if ident:
            if not isinstance(node, dict):
                return None
            node = node.get(ident)
        elif idx != "":
            if not isinstance(node, list):
                return None
            i = int(idx)
            if i >= len(node):
                return None
            node = node[i]
        if node is None:
            return None
    return node


def json_to_raw_item(
    body: dict[str, Any],
    *,
    mapping: WebhookFieldMapping,
    received_at_default: datetime | None = None,
) -> RawItem:
    external_id = _coerce_str(lookup_path(body, mapping.external_id))
    if not external_id:
        # Fallback: deterministic sha256 of the canonical body. Keeps dedupe
        # working even for senders that omit a vendor id.
        external_id = "sha256:" + hashlib.sha256(
            repr(sorted(body.items())).encode("utf-8")
        ).hexdigest()

    received_at = _coerce_dt(
        lookup_path(body, mapping.received_at)
    ) or (received_at_default or datetime.now(UTC))

    sender = _coerce_str(lookup_path(body, mapping.sender))
    subject = _coerce_str(lookup_path(body, mapping.subject))
    body_text = _coerce_str(lookup_path(body, mapping.body_text))
    body_html = _coerce_str(lookup_path(body, mapping.body_html))
    primary_link = _coerce_str(lookup_path(body, mapping.primary_link))

    links = [{"url": primary_link, "anchor": subject or ""}] if primary_link else []

    return RawItem(
        external_id=external_id,
        received_at=received_at,
        sender=sender,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        links=links,
        payload={"json": body, "mapping": mapping.model_dump()},
    )


def _coerce_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _coerce_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, (int, float)):
        # epoch seconds; vendors sometimes ship ms
        ts = float(value)
        if ts > 1e12:
            ts /= 1000.0
        return datetime.fromtimestamp(ts, tz=UTC)
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
        except ValueError:
            return None
    return None
