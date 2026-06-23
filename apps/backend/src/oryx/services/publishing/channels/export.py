"""Export channel adapter (§10.2).

No external API. publish() renders the draft as a Markdown file under a
configurable local base directory and returns the file path as external_url.
No credentials are needed — validate_credentials and health_check are always
true.
"""
from __future__ import annotations

import asyncio
import re
import uuid
from pathlib import Path
from typing import Any

from oryx.config import get_settings
from oryx.services.publishing.channels.base import (
    ChannelError,
    PublishResult,
)
from oryx.services.publishing.channels.formatting import single_segment

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slug(title: str) -> str:
    s = _SLUG_RE.sub("-", title.lower()).strip("-")
    return (s or "draft")[:60]


class ExportChannel:
    channel_type = "export"

    def __init__(self, base_dir: str | None = None) -> None:
        self._base_dir = base_dir or get_settings().publish_export_dir

    async def validate_credentials(self, credentials: dict[str, Any]) -> bool:
        return True  # no credentials for export

    async def health_check(self, credentials: dict[str, Any]) -> bool:
        return True

    def format_content(self, content: str, max_length: int | None) -> list[str]:
        return single_segment(content, max_length)

    async def publish(
        self,
        content: str,
        draft_title: str,
        credentials: dict[str, Any],
        config: dict[str, Any],
    ) -> PublishResult:
        base = Path(config.get("base_dir") or self._base_dir)
        file_id = uuid.uuid4().hex
        document = f"# {draft_title}\n\n{content}\n"

        def _write() -> Path:
            base.mkdir(parents=True, exist_ok=True)
            path = base / f"{_slug(draft_title)}-{file_id}.md"
            path.write_text(document, encoding="utf-8")
            return path.resolve()

        try:
            # Blocking filesystem I/O off the event loop (matches the SMTP path).
            resolved = await asyncio.to_thread(_write)
        except OSError as exc:
            # A filesystem failure is not retryable in any useful way here.
            raise ChannelError(f"{self.channel_type}: write failed: {exc}") from exc

        return PublishResult(
            external_id=file_id,
            external_url=str(resolved),
            status="delivered",
        )
