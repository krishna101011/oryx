"""Twitter/X channel adapter (§10.2).

Posts a draft as a tweet (or numbered thread) via Twitter API v2. format_content
splits at sentence boundaries into ≤280-char segments; threads post
sequentially, each reply chained to the previous via in_reply_to_tweet_id. The
first tweet's id is the publication external_id.
"""
from __future__ import annotations

from typing import Any

import httpx

from oryx.services.publishing.channels.base import (
    PublishResult,
    TransientChannelError,
)
from oryx.services.publishing.channels.formatting import thread_segments
from oryx.services.publishing.channels.http import raise_for_status

_TWEETS_URL = "https://api.twitter.com/2/tweets"
_ME_URL = "https://api.twitter.com/2/users/me"
_MAX_TWEET = 280


class TwitterXChannel:
    channel_type = "twitter_x"

    def __init__(self, timeout: float = 30.0) -> None:
        self._timeout = timeout

    async def validate_credentials(self, credentials: dict[str, Any]) -> bool:
        # User-context posting needs an access token; the rest of the OAuth app
        # fields are config-time concerns, not required to accept the target.
        return bool(credentials.get("access_token"))

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
        return thread_segments(content, max_length or _MAX_TWEET)

    async def publish(
        self,
        content: str,
        draft_title: str,
        credentials: dict[str, Any],
        config: dict[str, Any],
    ) -> PublishResult:
        token = credentials.get("access_token")
        segments = self.format_content(content, _MAX_TWEET) or [content[:_MAX_TWEET]]
        headers = {
            "Authorization": f"Bearer {token}",
            "content-type": "application/json",
        }
        first_id: str | None = None
        reply_to: str | None = None
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                for segment in segments:
                    body: dict[str, Any] = {"text": segment}
                    if reply_to is not None:
                        body["reply"] = {"in_reply_to_tweet_id": reply_to}
                    resp = await client.post(_TWEETS_URL, headers=headers, json=body)
                    raise_for_status(resp, channel=self.channel_type)
                    tweet_id = (resp.json().get("data") or {}).get("id")
                    if first_id is None:
                        first_id = tweet_id
                    reply_to = tweet_id
        except httpx.HTTPError as exc:
            raise TransientChannelError(
                f"{self.channel_type}: unreachable: {exc}"
            ) from exc

        url = (
            f"https://twitter.com/i/web/status/{first_id}" if first_id else None
        )
        return PublishResult(
            external_id=first_id, external_url=url, status="delivered"
        )
