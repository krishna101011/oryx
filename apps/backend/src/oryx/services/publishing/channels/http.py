"""Shared HTTP helpers for channel adapters.

Centralises the status-code → ChannelError mapping (§16.3) so every HTTP-based
channel classifies failures identically:
  401 / 403            → PermanentChannelError (bad/again-bad credentials)
  429 / 5xx / network  → TransientChannelError (retryable)
  other 4xx            → PermanentChannelError (malformed request — retry won't help)
"""
from __future__ import annotations

from typing import Any

import httpx

from oryx.services.publishing.channels.base import (
    PermanentChannelError,
    TransientChannelError,
)


def raise_for_status(resp: httpx.Response, *, channel: str) -> None:
    code = resp.status_code
    if code < 400:
        return
    body = resp.text[:200]
    if code in (401, 403):
        raise PermanentChannelError(f"{channel}: auth rejected ({code}): {body}")
    if code == 429 or code >= 500:
        raise TransientChannelError(f"{channel}: retryable {code}: {body}")
    raise PermanentChannelError(f"{channel}: request rejected {code}: {body}")


async def post_json(
    url: str,
    *,
    channel: str,
    headers: dict[str, str] | None = None,
    json: Any = None,
    timeout: float = 30.0,
) -> httpx.Response:
    """POST JSON and translate transport errors to TransientChannelError.

    A real httpx.AsyncClient is used so webhook/export-style channels run truly
    end-to-end; tests for credentialed channels patch httpx.AsyncClient.post.
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=headers, json=json)
    except httpx.HTTPError as exc:
        raise TransientChannelError(f"{channel}: unreachable: {exc}") from exc
    raise_for_status(resp, channel=channel)
    return resp


async def get(
    url: str,
    *,
    channel: str,
    headers: dict[str, str] | None = None,
    timeout: float = 15.0,
) -> httpx.Response:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        raise TransientChannelError(f"{channel}: unreachable: {exc}") from exc
    return resp
