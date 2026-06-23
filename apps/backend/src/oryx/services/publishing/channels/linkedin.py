"""LinkedIn channel adapter (§10.2).

Posts a single member share via the ugcPosts endpoint. format_content caps at
3000 chars (no splitting — LinkedIn is a single post). External id is the
returned post URN.
"""
from __future__ import annotations

from typing import Any

import httpx

from oryx.services.publishing.channels.base import (
    PublishResult,
    TransientChannelError,
)
from oryx.services.publishing.channels.formatting import single_segment
from oryx.services.publishing.channels.http import raise_for_status

_UGC_URL = "https://api.linkedin.com/v2/ugcPosts"
_ME_URL = "https://api.linkedin.com/v2/me"
_MAX_POST = 3000


class LinkedInChannel:
    channel_type = "linkedin"

    def __init__(self, timeout: float = 30.0) -> None:
        self._timeout = timeout

    async def validate_credentials(self, credentials: dict[str, Any]) -> bool:
        return bool(credentials.get("access_token") and credentials.get("person_urn"))

    async def health_check(self, credentials: dict[str, Any]) -> bool:
        token = credentials.get("access_token")
        if not token:
            return False
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    _ME_URL, headers={"Authorization": f"Bearer {token}"}
                )
        except httpx.HTTPError:
            return False
        return resp.status_code == 200

    def format_content(self, content: str, max_length: int | None) -> list[str]:
        return single_segment(content, max_length or _MAX_POST)

    async def publish(
        self,
        content: str,
        draft_title: str,
        credentials: dict[str, Any],
        config: dict[str, Any],
    ) -> PublishResult:
        token = credentials.get("access_token")
        author = credentials.get("person_urn")
        segments = self.format_content(content, _MAX_POST)
        text = segments[0] if segments else ""
        body = {
            "author": author,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            },
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "content-type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(_UGC_URL, headers=headers, json=body)
                raise_for_status(resp, channel=self.channel_type)
        except httpx.HTTPError as exc:
            raise TransientChannelError(
                f"{self.channel_type}: unreachable: {exc}"
            ) from exc

        # LinkedIn returns the URN in the X-RestLi-Id header (and/or body.id).
        urn = resp.headers.get("x-restli-id") or (resp.json() or {}).get("id")
        url = (
            f"https://www.linkedin.com/feed/update/{urn}" if urn else None
        )
        return PublishResult(external_id=urn, external_url=url, status="delivered")
