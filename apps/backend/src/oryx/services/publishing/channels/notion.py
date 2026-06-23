"""Notion channel adapter (§10.2).

Creates a new page under config.parent_page_id via Notion API v1. Plain content
is mapped into basic paragraph blocks (no rich formatting this wave — one
paragraph block per non-empty line, chunked to Notion's 2000-char rich-text
limit). External id/url are the created page id/url.
"""
from __future__ import annotations

from typing import Any

import httpx

from oryx.services.publishing.channels.base import (
    PermanentChannelError,
    PublishResult,
    TransientChannelError,
)
from oryx.services.publishing.channels.formatting import single_segment
from oryx.services.publishing.channels.http import get, raise_for_status

_PAGES_URL = "https://api.notion.com/v1/pages"
_USERS_ME_URL = "https://api.notion.com/v1/users/me"
_NOTION_VERSION = "2022-06-28"
_BLOCK_LIMIT = 2000


def _paragraph_blocks(content: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        for i in range(0, len(line), _BLOCK_LIMIT):
            chunk = line[i : i + _BLOCK_LIMIT]
            blocks.append(
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {"type": "text", "text": {"content": chunk}}
                        ]
                    },
                }
            )
    return blocks


class NotionChannel:
    channel_type = "notion"

    def __init__(self, timeout: float = 30.0) -> None:
        self._timeout = timeout

    def _headers(self, token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "Notion-Version": _NOTION_VERSION,
            "content-type": "application/json",
        }

    async def validate_credentials(self, credentials: dict[str, Any]) -> bool:
        return bool(credentials.get("integration_token"))

    async def health_check(self, credentials: dict[str, Any]) -> bool:
        token = credentials.get("integration_token")
        if not token:
            return False
        try:
            resp = await get(
                _USERS_ME_URL,
                channel=self.channel_type,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Notion-Version": _NOTION_VERSION,
                },
                timeout=self._timeout,
            )
        except TransientChannelError:
            return False
        return resp.status_code == 200

    def format_content(self, content: str, max_length: int | None) -> list[str]:
        return single_segment(content, max_length)

    async def publish(
        self,
        content: str,
        draft_title: str,
        credentials: dict[str, Any],
        config: dict[str, Any],
    ) -> PublishResult:
        token = str(credentials.get("integration_token") or "")
        parent_page_id = config.get("parent_page_id")
        if not parent_page_id:
            raise PermanentChannelError(
                f"{self.channel_type}: config.parent_page_id is required"
            )
        body = {
            "parent": {"page_id": parent_page_id},
            "properties": {
                "title": {
                    "title": [{"type": "text", "text": {"content": draft_title}}]
                }
            },
            "children": _paragraph_blocks(content),
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    _PAGES_URL, headers=self._headers(token), json=body
                )
                raise_for_status(resp, channel=self.channel_type)
        except httpx.HTTPError as exc:
            raise TransientChannelError(
                f"{self.channel_type}: unreachable: {exc}"
            ) from exc

        data = resp.json() or {}
        page_id = data.get("id")
        url = data.get("url")
        return PublishResult(
            external_id=page_id, external_url=url, status="delivered"
        )
