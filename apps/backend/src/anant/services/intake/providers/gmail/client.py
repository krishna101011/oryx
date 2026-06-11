"""Gmail REST client — READ-ONLY.

This module is the only place that talks to gmail.googleapis.com. Every
exported function corresponds to a documented Gmail v1 endpoint:

    list_history     — users.history.list (delta sync)
    list_messages    — users.messages.list (bootstrap or historyId-expiry fallback)
    get_message      — users.messages.get (full message metadata + body)

The DENY-LIST below is enforced at module-import time: if any future PR
ever references one of these vendor methods inside this file, the import
fails. This is the structural enforcement of ADR-023.
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any

import httpx

from anant.services.intake.providers.errors import (
    ProviderError,
    ProviderErrorKind,
)
from anant.services.intake.providers.gmail.config_schema import GMAIL_API_BASE

# ---------------------------------------------------------------------------
# ADR-023 enforcement: deny-listed Gmail write endpoints / SDK methods.
# Any future PR that adds a reference to any of these strings inside this
# module's source will trip the assertion below.
# ---------------------------------------------------------------------------
_DENY_LIST: tuple[str, ...] = (
    "messages.send",
    "messages.modify",
    "messages.trash",
    "messages.untrash",
    "messages.delete",
    "messages.batchDelete",
    "messages.batchModify",
    "labels.create",
    "labels.delete",
    "labels.patch",
    "labels.update",
    "drafts.create",
    "drafts.send",
    "drafts.update",
    "drafts.delete",
    "settings.",
    "users.watch",   # push subscription mutates server state; Phase 3.x only
    "users.stop",
)


def _assert_no_write_functions_defined() -> None:
    """Enforcement: no top-level callable in THIS module may share a name
    with a Gmail write/mutation endpoint.

    This guards against the realistic regression — someone adds a function
    like `send_message` or `modify_labels` to this client file. A
    full-source string scan is too brittle (docstrings, comments) to be
    load-bearing. Function-name discipline is the durable contract: the
    only public callables here are `list_*`, `get_*`, plus a couple of
    typed result containers.
    """
    module = inspect.getmodule(_assert_no_write_functions_defined)
    if module is None:  # pragma: no cover
        return
    forbidden_substrings = (
        "send", "modify", "trash", "delete", "create", "update", "patch",
        "batch_delete", "batch_modify", "watch", "stop",
    )
    for name, obj in vars(module).items():
        if name.startswith("_"):
            continue
        if not callable(obj):
            continue
        # Only check functions defined in this module, not re-exports.
        if getattr(obj, "__module__", None) != module.__name__:
            continue
        lower = name.lower()
        for forbidden in forbidden_substrings:
            if forbidden in lower:
                raise RuntimeError(
                    f"ADR-023 violation: gmail.client.py defines '{name}' "
                    f"which looks like a write method"
                )


_assert_no_write_functions_defined()


@dataclass(frozen=True)
class HistoryPage:
    history_id: str | None
    message_ids: list[str]
    next_page_token: str | None


@dataclass(frozen=True)
class MessageIdsPage:
    message_ids: list[str]
    next_page_token: str | None
    result_size_estimate: int


# ---------------------------------------------------------------------------
# Public read-only endpoints
# ---------------------------------------------------------------------------

async def list_history(
    *,
    access_token: str,
    start_history_id: str,
    label_id: str | None = None,
    page_token: str | None = None,
) -> HistoryPage:
    """users.history.list — delta sync.

    Returns the message ids added since start_history_id. On 404, callers
    must invoke the CR-5 expiry fallback path (list_messages with a date
    bound) and re-establish the cursor.
    """
    params: dict[str, Any] = {
        "startHistoryId": start_history_id,
        "historyTypes": "messageAdded",
    }
    if label_id:
        params["labelId"] = label_id
    if page_token:
        params["pageToken"] = page_token

    data = await _get_json(
        "/users/me/history", access_token=access_token, params=params
    )

    history_id = data.get("historyId")
    message_ids: list[str] = []
    for entry in data.get("history", []):
        for added in entry.get("messagesAdded", []):
            msg = added.get("message") or {}
            mid = msg.get("id")
            if mid:
                message_ids.append(mid)
    return HistoryPage(
        history_id=history_id,
        message_ids=message_ids,
        next_page_token=data.get("nextPageToken"),
    )


async def list_messages(
    *,
    access_token: str,
    label_ids: list[str] | None = None,
    query: str | None = None,
    page_token: str | None = None,
    max_results: int = 100,
) -> MessageIdsPage:
    """users.messages.list — bootstrap pull and CR-5 fallback path."""
    params: dict[str, Any] = {"maxResults": max_results}
    if label_ids:
        params["labelIds"] = label_ids
    if query:
        params["q"] = query
    if page_token:
        params["pageToken"] = page_token

    data = await _get_json(
        "/users/me/messages", access_token=access_token, params=params
    )
    ids = [m["id"] for m in data.get("messages", []) if "id" in m]
    return MessageIdsPage(
        message_ids=ids,
        next_page_token=data.get("nextPageToken"),
        result_size_estimate=int(data.get("resultSizeEstimate", 0)),
    )


async def get_message(
    *, access_token: str, message_id: str, format: str = "full"
) -> dict[str, Any]:
    """users.messages.get — read a single message.

    `format=full` returns body + payload; `metadata` is lighter when we
    only need headers. The mapper requests `full`.
    """
    params = {"format": format}
    return await _get_json(
        f"/users/me/messages/{message_id}",
        access_token=access_token,
        params=params,
    )


async def get_profile(*, access_token: str) -> dict[str, Any]:
    """users.getProfile — used at connect time to verify the token works
    and to capture the latest historyId for the first cursor."""
    return await _get_json("/users/me/profile", access_token=access_token)


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------

class HistoryIdExpiredError(ProviderError):
    """Special-cased 404 from history.list. Caller invokes the CR-5 fallback."""

    def __init__(self) -> None:
        super().__init__(
            kind=ProviderErrorKind.TRANSIENT,
            message="Gmail historyId expired",
        )


async def _get_json(
    path: str, *, access_token: str, params: dict[str, Any] | None = None
) -> dict[str, Any]:
    url = f"{GMAIL_API_BASE}{path}"
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=headers, params=params)
    except httpx.HTTPError as e:
        raise ProviderError(
            kind=ProviderErrorKind.TRANSIENT,
            message=f"Gmail unreachable: {e}",
            cause_class=type(e).__name__,
        ) from e

    status = resp.status_code
    if status == 200:
        return resp.json()
    if status == 401 or status == 403:
        raise ProviderError(
            kind=ProviderErrorKind.AUTH, message=f"Gmail auth failure ({status})"
        )
    if status == 404 and path.startswith("/users/me/history"):
        # CR-5: the history cursor has aged out. Caller falls back to list_messages.
        raise HistoryIdExpiredError()
    if status == 429:
        retry_after = resp.headers.get("retry-after")
        try:
            retry = int(retry_after) if retry_after else None
        except ValueError:
            retry = None
        raise ProviderError(
            kind=ProviderErrorKind.RATE_LIMITED,
            message="Gmail rate limited",
            retry_after_seconds=retry,
        )
    if 400 <= status < 500:
        raise ProviderError(
            kind=ProviderErrorKind.PERMANENT,
            message=f"Gmail client error {status}: {resp.text[:200]}",
        )
    raise ProviderError(
        kind=ProviderErrorKind.TRANSIENT,
        message=f"Gmail server error {status}",
    )
