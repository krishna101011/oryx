"""Pluggable video-hosting provider abstraction. Mirrors core/ai_provider.py
and core/payment_provider.py's exact shape: one narrow Protocol, vendor
errors collapsed onto a shared taxonomy before crossing the boundary, a
factory that picks the concrete implementation so callers never branch on
vendor.

Real decision (docs/PHASE_8_TRAINING_ARCHITECTURE.md §3): Cloudflare
Stream, chosen over self-built infrastructure (expensive, complex, and
lower-quality at this scale) and over Mux (5-8x higher cost, justified by
live-streaming/analytics features Academy doesn't need). Bundled encoding
+ adaptive HLS delivery — no separate transcoding pipeline to build or
maintain.

FOUNDATION WAVE: create_upload_url/get_asset_status/delete_asset are real
HTTP calls shaped exactly like Cloudflare's own Stream REST API, but no
live credential is configured by default (Settings.cloudflare_stream_
account_id / cloudflare_stream_api_token are None) — CloudflareStreamProvider
raises VideoProviderError(PERMANENT) pre-flight, exactly like
OpenAICompatProvider's missing-config guard in ai_provider.py and
StripeProvider's missing-API-key guard in payment_provider.py. No live
video upload or playback is wired this wave — that needs real Cloudflare
credentials neither the dev nor the assistant has yet. Lesson.video_asset_id
(core/models.py) stores whatever create_upload_url eventually returns as
its asset_id — a Cloudflare Stream video uid, never a raw file path.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol, runtime_checkable

import httpx

_CLOUDFLARE_STREAM_BASE = "https://api.cloudflare.com/client/v4/accounts/{account_id}/stream"


class VideoProviderErrorKind(str, Enum):
    TRANSIENT = "transient"        # 5xx, network blip, timeout
    RATE_LIMITED = "rate_limited"  # 429
    AUTH = "auth"                  # API token rejected
    PERMANENT = "permanent"        # missing config, bad request, unknown asset
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class VideoProviderError(Exception):
    kind: VideoProviderErrorKind
    message: str
    provider: str
    retry_after_seconds: int | None = None

    def __str__(self) -> str:  # pragma: no cover — trivial
        return f"{self.provider}/{self.kind.value}: {self.message}"


@dataclass(frozen=True)
class VideoUploadHandle:
    """Returned by create_upload_url. asset_id is the vendor's own video
    identifier (Cloudflare Stream's `uid`) — the durable reference stored
    on Lesson.video_asset_id. upload_url is a one-time direct-upload URL
    the (not-yet-built) authoring client PUTs the raw video file to; ORYX's
    own backend never proxies the video bytes."""

    asset_id: str
    upload_url: str
    raw: dict[str, Any]


@dataclass(frozen=True)
class VideoAssetStatus:
    """Returned by get_asset_status. `ready` mirrors Cloudflare Stream's own
    readyToStream flag — false while the vendor is still encoding. Playback
    URLs are None until ready."""

    asset_id: str
    ready: bool
    playback_hls_url: str | None
    playback_dash_url: str | None
    duration_seconds: float | None
    raw: dict[str, Any]


@runtime_checkable
class VideoProvider(Protocol):
    name: str

    async def create_upload_url(self, *, lesson_id: str) -> VideoUploadHandle:
        """lesson_id is stashed in the vendor's own metadata (Cloudflare
        Stream's `meta` field) purely for traceability — the returned
        asset_id, not lesson_id, is what gets stored on
        Lesson.video_asset_id."""
        ...

    async def get_asset_status(self, *, asset_id: str) -> VideoAssetStatus: ...

    async def delete_asset(self, *, asset_id: str) -> None: ...


class CloudflareStreamProvider:
    """Direct Cloudflare Stream REST API. Vendor errors map onto
    VideoProviderError so callers never branch on vendor-specific
    exceptions — the same AnthropicProvider/StripeProvider precedent."""

    name = "cloudflare_stream"

    def __init__(
        self,
        account_id: str | None,
        api_token: str | None,
        timeout: float = 30.0,
    ) -> None:
        self._account_id = account_id
        self._api_token = api_token
        self._timeout = timeout

    def _require_config(self) -> tuple[str, str]:
        if not (self._account_id and self._api_token):
            raise VideoProviderError(
                kind=VideoProviderErrorKind.PERMANENT,
                message=(
                    "CLOUDFLARE_STREAM_ACCOUNT_ID/CLOUDFLARE_STREAM_API_TOKEN "
                    "are not configured"
                ),
                provider=self.name,
            )
        return self._account_id, self._api_token

    async def create_upload_url(self, *, lesson_id: str) -> VideoUploadHandle:
        account_id, api_token = self._require_config()
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{_CLOUDFLARE_STREAM_BASE.format(account_id=account_id)}/direct_upload",
                    headers={"authorization": f"Bearer {api_token}"},
                    json={"meta": {"lessonId": lesson_id}, "maxDurationSeconds": 3600},
                )
        except httpx.HTTPError as exc:
            raise VideoProviderError(
                kind=VideoProviderErrorKind.TRANSIENT,
                message=f"Cloudflare Stream unreachable: {exc}",
                provider=self.name,
            ) from exc
        self._raise_for_status(resp)
        data: dict[str, Any] = resp.json()
        result = data.get("result") or {}
        return VideoUploadHandle(
            asset_id=result.get("uid", ""),
            upload_url=result.get("uploadURL", ""),
            raw=data,
        )

    async def get_asset_status(self, *, asset_id: str) -> VideoAssetStatus:
        account_id, api_token = self._require_config()
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    f"{_CLOUDFLARE_STREAM_BASE.format(account_id=account_id)}/{asset_id}",
                    headers={"authorization": f"Bearer {api_token}"},
                )
        except httpx.HTTPError as exc:
            raise VideoProviderError(
                kind=VideoProviderErrorKind.TRANSIENT,
                message=f"Cloudflare Stream unreachable: {exc}",
                provider=self.name,
            ) from exc
        self._raise_for_status(resp)
        data: dict[str, Any] = resp.json()
        result = data.get("result") or {}
        playback = result.get("playback") or {}
        return VideoAssetStatus(
            asset_id=asset_id,
            ready=bool(result.get("readyToStream")),
            playback_hls_url=playback.get("hls"),
            playback_dash_url=playback.get("dash"),
            duration_seconds=result.get("duration"),
            raw=data,
        )

    async def delete_asset(self, *, asset_id: str) -> None:
        account_id, api_token = self._require_config()
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.delete(
                    f"{_CLOUDFLARE_STREAM_BASE.format(account_id=account_id)}/{asset_id}",
                    headers={"authorization": f"Bearer {api_token}"},
                )
        except httpx.HTTPError as exc:
            raise VideoProviderError(
                kind=VideoProviderErrorKind.TRANSIENT,
                message=f"Cloudflare Stream unreachable: {exc}",
                provider=self.name,
            ) from exc
        self._raise_for_status(resp)

    def _raise_for_status(self, resp: httpx.Response) -> None:
        if resp.status_code in (401, 403):
            raise VideoProviderError(
                kind=VideoProviderErrorKind.AUTH,
                message="Cloudflare Stream API token rejected",
                provider=self.name,
            )
        if resp.status_code == 429:
            retry_after = resp.headers.get("retry-after")
            raise VideoProviderError(
                kind=VideoProviderErrorKind.RATE_LIMITED,
                message="Cloudflare Stream rate limit",
                provider=self.name,
                retry_after_seconds=int(retry_after) if retry_after else None,
            )
        if resp.status_code >= 500:
            raise VideoProviderError(
                kind=VideoProviderErrorKind.TRANSIENT,
                message=f"Cloudflare Stream API {resp.status_code}",
                provider=self.name,
            )
        if resp.status_code >= 400:
            raise VideoProviderError(
                kind=VideoProviderErrorKind.PERMANENT,
                message=f"Cloudflare Stream API {resp.status_code}: {resp.text[:200]}",
                provider=self.name,
            )


def get_video_provider(settings) -> VideoProvider:
    """Factory. Only one vendor exists today (Cloudflare Stream, §3's real
    decision) — no branching, matching get_stripe_provider's shape for a
    single concrete implementation."""
    return CloudflareStreamProvider(
        account_id=getattr(settings, "cloudflare_stream_account_id", None),
        api_token=getattr(settings, "cloudflare_stream_api_token", None),
    )
