"""HTTP transport for the API pull provider.

This module is the only place that performs an outbound HTTP request on
behalf of an api_pull source. SSRF guard is invoked here on EVERY URL —
defense in depth in case a vendor SDK ever bypasses the orchestrator.

Auth methods locked in Batch 2:
  - bearer: Authorization: Bearer <token>
  - api_key_header: <header_name>: <token>
  - oauth2_client_credentials: Authorization: Bearer <token-from-cache>
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx

from anant.services.intake.providers.api_pull.config_schema import (
    ApiPullSourceConfig,
)
from anant.services.intake.providers.api_pull.oauth2_cc import (
    get_client_credentials_token,
)
from anant.services.intake.providers.api_pull.safety import assert_url_safe
from anant.services.intake.providers.errors import (
    ProviderError,
    ProviderErrorKind,
)

DEFAULT_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class FetchedResponse:
    body: dict[str, Any]
    final_url: str


@dataclass(frozen=True)
class ResolvedCredentials:
    """Whatever's needed to build the auth header for this source.

    For bearer + api_key_header: `token` is the static credential.
    For oauth2: `client_id` + `client_secret` are present, `token` is None
    and will be fetched on demand.
    """

    token: str | None = None
    client_id: str | None = None
    client_secret: str | None = None


async def fetch_endpoint(
    *,
    config: ApiPullSourceConfig,
    creds: ResolvedCredentials,
    path: str,
    params: dict[str, str],
) -> FetchedResponse:
    url = _join_url(str(config.base_url), path)
    # SSRF guard runs against the final URL before we connect.
    assert_url_safe(url, hostname_allowlist=list(config.hostname_allowlist))

    headers: dict[str, str] = {
        "Accept": "application/json",
        "User-Agent": "AnantIntake/1.0 (+https://anant.capital)",
    }
    await _apply_auth(config, creds, headers)

    try:
        async with httpx.AsyncClient(
            timeout=DEFAULT_TIMEOUT_SECONDS, follow_redirects=False
        ) as client:
            resp = await client.get(url, headers=headers, params=params)
    except httpx.HTTPError as e:
        raise ProviderError(
            kind=ProviderErrorKind.TRANSIENT,
            message=f"HTTP error fetching {url}: {e}",
        ) from e

    status = resp.status_code
    if status in (401, 403):
        raise ProviderError(kind=ProviderErrorKind.AUTH, message=f"Auth failure ({status})")
    if status == 429:
        retry_after = resp.headers.get("retry-after")
        try:
            ra = int(retry_after) if retry_after else None
        except ValueError:
            ra = None
        raise ProviderError(
            kind=ProviderErrorKind.RATE_LIMITED,
            message="Rate limited",
            retry_after_seconds=ra,
        )
    if 400 <= status < 500:
        raise ProviderError(
            kind=ProviderErrorKind.PERMANENT,
            message=f"Client error {status}: {resp.text[:200]}",
        )
    if status >= 500:
        raise ProviderError(
            kind=ProviderErrorKind.TRANSIENT, message=f"Server error {status}"
        )

    body_bytes = resp.content
    if len(body_bytes) > config.max_response_bytes:
        raise ProviderError(
            kind=ProviderErrorKind.PERMANENT,
            message=f"Response exceeds {config.max_response_bytes} bytes",
        )

    try:
        body = json.loads(body_bytes.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ProviderError(
            kind=ProviderErrorKind.PERMANENT,
            message=f"Response not valid JSON: {e}",
        ) from e
    if not isinstance(body, (dict, list)):
        raise ProviderError(
            kind=ProviderErrorKind.PERMANENT,
            message="Response root must be object or array",
        )
    # Wrap arrays so the rest of the pipeline always sees a dict at root.
    if isinstance(body, list):
        body = {"items": body}
    return FetchedResponse(body=body, final_url=str(resp.url))


async def _apply_auth(
    config: ApiPullSourceConfig,
    creds: ResolvedCredentials,
    headers: dict[str, str],
) -> None:
    if config.auth_method == "bearer":
        if not creds.token:
            raise ProviderError(
                kind=ProviderErrorKind.AUTH,
                message="bearer auth requires a token in credentials",
            )
        headers["Authorization"] = f"Bearer {creds.token}"
    elif config.auth_method == "api_key_header":
        if not config.api_key_header_name:
            raise ProviderError(
                kind=ProviderErrorKind.PERMANENT,
                message="api_key_header method requires api_key_header_name in config",
            )
        if not creds.token:
            raise ProviderError(
                kind=ProviderErrorKind.AUTH,
                message="api_key_header auth requires a token in credentials",
            )
        headers[config.api_key_header_name] = creds.token
    elif config.auth_method == "oauth2_client_credentials":
        if not config.oauth2_token_url or not creds.client_id or not creds.client_secret:
            raise ProviderError(
                kind=ProviderErrorKind.PERMANENT,
                message="oauth2_client_credentials requires oauth2_token_url + client_id + client_secret",
            )
        token = await get_client_credentials_token(
            token_url=str(config.oauth2_token_url),
            client_id=creds.client_id,
            client_secret=creds.client_secret,
            scope=config.oauth2_scope,
        )
        headers["Authorization"] = f"Bearer {token}"


def _join_url(base: str, path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return base.rstrip("/") + "/" + path.lstrip("/")
