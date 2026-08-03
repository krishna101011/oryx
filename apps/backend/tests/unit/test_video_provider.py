"""core/video_provider.py — Phase 8 Wave A. Mirrors test_payment_provider.py's
unconfigured-state coverage: CloudflareStreamProvider must raise a clean,
typed VideoProviderError(PERMANENT) pre-flight when no real credentials
exist, never attempt a live call, never crash raw.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest

from oryx.core.video_provider import (
    CloudflareStreamProvider,
    VideoProviderError,
    VideoProviderErrorKind,
    get_video_provider,
)


def _unconfigured_provider() -> CloudflareStreamProvider:
    return CloudflareStreamProvider(account_id=None, api_token=None)


@pytest.mark.asyncio
async def test_create_upload_url_rejects_unconfigured_credentials() -> None:
    provider = _unconfigured_provider()
    with pytest.raises(VideoProviderError) as exc:
        await provider.create_upload_url(lesson_id="lesson-1")
    assert exc.value.kind == VideoProviderErrorKind.PERMANENT
    assert "CLOUDFLARE_STREAM_ACCOUNT_ID" in exc.value.message


@pytest.mark.asyncio
async def test_get_asset_status_rejects_unconfigured_credentials() -> None:
    provider = _unconfigured_provider()
    with pytest.raises(VideoProviderError) as exc:
        await provider.get_asset_status(asset_id="asset-1")
    assert exc.value.kind == VideoProviderErrorKind.PERMANENT


@pytest.mark.asyncio
async def test_delete_asset_rejects_unconfigured_credentials() -> None:
    provider = _unconfigured_provider()
    with pytest.raises(VideoProviderError) as exc:
        await provider.delete_asset(asset_id="asset-1")
    assert exc.value.kind == VideoProviderErrorKind.PERMANENT


def test_factory_reads_settings_and_defaults_to_none() -> None:
    provider = get_video_provider(SimpleNamespace())
    assert isinstance(provider, CloudflareStreamProvider)
    assert provider.name == "cloudflare_stream"


def test_factory_wires_real_settings_fields() -> None:
    settings = SimpleNamespace(
        cloudflare_stream_account_id="acct_1", cloudflare_stream_api_token="tok_1"
    )
    provider = get_video_provider(settings)
    assert provider._account_id == "acct_1"
    assert provider._api_token == "tok_1"


@pytest.mark.asyncio
async def test_auth_rejected_maps_to_auth_kind() -> None:
    """Real status->kind mapping, same scheme as AnthropicProvider/
    StripeProvider (401 -> AUTH), proven against a patched HTTP layer
    rather than asserted by inspection only."""
    provider = CloudflareStreamProvider(account_id="acct_1", api_token="bad_token")

    async def fake_post(self, url, **kw):
        return httpx.Response(401, json={"success": False}, request=httpx.Request("POST", url))

    with patch.object(httpx.AsyncClient, "post", fake_post):
        with pytest.raises(VideoProviderError) as exc:
            await provider.create_upload_url(lesson_id="lesson-1")
    assert exc.value.kind == VideoProviderErrorKind.AUTH


@pytest.mark.asyncio
async def test_rate_limit_maps_to_rate_limited_kind_with_retry_hint() -> None:
    provider = CloudflareStreamProvider(account_id="acct_1", api_token="tok_1")

    async def fake_post(self, url, **kw):
        return httpx.Response(
            429,
            json={"success": False},
            headers={"retry-after": "30"},
            request=httpx.Request("POST", url),
        )

    with patch.object(httpx.AsyncClient, "post", fake_post):
        with pytest.raises(VideoProviderError) as exc:
            await provider.create_upload_url(lesson_id="lesson-1")
    assert exc.value.kind == VideoProviderErrorKind.RATE_LIMITED
    assert exc.value.retry_after_seconds == 30
