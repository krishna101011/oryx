"""Response → list of RawItems.

Reuses the webhook mapper's dotted-path extraction (DRY — same shape).
The only new wrinkle is locating the items array inside the response
when `items_field` is configured.
"""
from __future__ import annotations

from typing import Any

from oryx.services.intake.providers.base import RawItem
from oryx.services.intake.providers.webhook.config_schema import (
    WebhookFieldMapping,
)
from oryx.services.intake.providers.webhook.mapper import (
    json_to_raw_item,
    lookup_path,
)


def extract_items(
    body: dict[str, Any], items_field: str | None
) -> list[dict[str, Any]]:
    if not items_field:
        # Response root may be a wrapped array (see client.py — arrays get
        # wrapped under "items") or a dict whose values are the items.
        if isinstance(body.get("items"), list):
            return body["items"]
        return []
    found = lookup_path(body, items_field)
    if isinstance(found, list):
        return found
    return []


def response_to_raw_items(
    *,
    body: dict[str, Any],
    items_field: str | None,
    mapping: WebhookFieldMapping,
) -> list[RawItem]:
    items_raw = extract_items(body, items_field)
    out: list[RawItem] = []
    for raw_json in items_raw:
        if not isinstance(raw_json, dict):
            continue
        out.append(json_to_raw_item(raw_json, mapping=mapping))
    return out


def extract_cursor(body: dict[str, Any], cursor_field: str | None) -> str | None:
    if not cursor_field:
        return None
    val = lookup_path(body, cursor_field)
    return str(val) if val is not None else None
