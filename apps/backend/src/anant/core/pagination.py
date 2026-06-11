"""Cursor pagination helpers.

Cursors are opaque base64-encoded strings; clients treat them as opaque
and the server is free to change the encoding without notice.
"""
from __future__ import annotations

import base64
import json
from typing import Any


def encode_cursor(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> dict[str, Any]:
    padding = "=" * (-len(cursor) % 4)
    raw = base64.urlsafe_b64decode(cursor + padding)
    decoded = json.loads(raw)
    if not isinstance(decoded, dict):
        raise ValueError("Cursor payload must be an object")
    return decoded
