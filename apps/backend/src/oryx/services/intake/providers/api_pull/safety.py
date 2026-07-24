"""SSRF defense adapter for api_pull.

The guard itself lives in oryx.core.security.ssrf — it moved there because it
now also guards RSS (rss/client.py) and publishing webhooks
(publishing/channels/webhook.py), not just api_pull. This module is a thin
translation layer: it keeps api_pull's existing contract (raise
ProviderError, not UnsafeUrlError) so callers and tests in this package
don't need to know about the shared implementation.
"""
from __future__ import annotations

from oryx.core.security.ssrf import UnsafeUrlError
from oryx.core.security.ssrf import assert_url_safe as _assert_url_safe
from oryx.services.intake.providers.errors import (
    ProviderError,
    ProviderErrorKind,
)


def assert_url_safe(
    url: str, *, hostname_allowlist: list[str] | None = None
) -> None:
    """Raise ProviderError(PERMANENT) if the URL would be unsafe to fetch."""
    try:
        _assert_url_safe(url, hostname_allowlist=hostname_allowlist)
    except UnsafeUrlError as e:
        raise ProviderError(
            kind=ProviderErrorKind.PERMANENT,
            message=str(e),
        ) from e
